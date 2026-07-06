"""
fetch_transcripts.py — pull YouTube transcripts for the corpus.

Strategy (in order of preference per video):
  1. youtube-transcript-api  (free, no key)
  2. Supadata /v1/youtube/transcript  (uses SUPADATA_API_KEY from .env)
  3. yt-dlp --skip-download --write-auto-subs  (falls back to VTT, cleaned)

Every video is retried through the fallbacks independently; one failure does
not kill the run. Failed videos are logged to research/sources.md by the
caller (this script just prints failures to stdout).

Usage:
    python scripts/fetch_transcripts.py \
        --author jason-bay \
        --videos videos.txt

    videos.txt format (one per line):
        <video_url_or_id>|<optional title override>

Files land at:
    research/youtube-transcripts/<author>/<YYYY-MM-DD>-<slug>.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
    )
    _HAS_YTA = True
except ImportError:
    _HAS_YTA = False

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


REPO_ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_ROOT = REPO_ROOT / "research" / "youtube-transcripts"
ENV_PATH = REPO_ROOT / ".env"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env()


VIDEO_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})"
)


def extract_video_id(url_or_id: str) -> Optional[str]:
    s = url_or_id.strip()
    if len(s) == 11 and re.fullmatch(r"[A-Za-z0-9_-]{11}", s):
        return s
    m = VIDEO_ID_RE.search(s)
    return m.group(1) if m else None


def slugify(text: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:maxlen].rstrip("-") or "untitled"


@dataclass
class Transcript:
    video_id: str
    text: str
    tool: str
    title: Optional[str] = None
    channel: Optional[str] = None
    publish_date: Optional[str] = None
    duration: Optional[str] = None


def try_youtube_transcript_api(video_id: str) -> Optional[Transcript]:
    if not _HAS_YTA:
        return None
    try:
        # v1.x API: instance method .fetch()
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        # FetchedTranscript is iterable, yielding FetchedTranscriptSnippet(text,...)
        parts = []
        for snip in fetched:
            t = getattr(snip, "text", None)
            if t is None and isinstance(snip, dict):
                t = snip.get("text")
            if t:
                parts.append(t.strip())
        text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        if not text:
            return None
        return Transcript(video_id=video_id, text=text, tool="youtube-transcript-api")
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        print(f"  yta: {type(e).__name__}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  yta error: {e}", file=sys.stderr)
        return None


def try_supadata(video_id: str) -> Optional[Transcript]:
    key = ENV.get("SUPADATA_API_KEY")
    if not key or not _HAS_REQUESTS:
        return None
    try:
        r = requests.get(
            "https://api.supadata.ai/v1/youtube/transcript",
            params={"videoId": video_id, "text": "true"},
            headers={"x-api-key": key},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"  supadata: HTTP {r.status_code}", file=sys.stderr)
            return None
        data = r.json()
        text = data.get("content") or data.get("text") or ""
        if isinstance(text, list):
            text = " ".join(
                seg.get("text", "") for seg in text if isinstance(seg, dict)
            )
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return None
        return Transcript(video_id=video_id, text=text, tool="supadata")
    except Exception as e:
        print(f"  supadata error: {e}", file=sys.stderr)
        return None


def try_ytdlp(video_id: str, workdir: Path) -> Optional[Transcript]:
    """Fallback: pull auto-subs via yt-dlp and clean the VTT."""
    workdir.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(workdir / f"{video_id}.%(ext)s")
    try:
        subprocess.run(
            [
                "yt-dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-langs", "en.*",
                "--sub-format", "vtt",
                "-o", out_tmpl,
                f"https://www.youtube.com/watch?v={video_id}",
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    except FileNotFoundError:
        print("  yt-dlp not installed", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"  yt-dlp failed: {e.stderr.decode('utf-8', 'ignore')[:200]}", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("  yt-dlp timeout", file=sys.stderr)
        return None

    vtt_files = list(workdir.glob(f"{video_id}.*.vtt"))
    if not vtt_files:
        return None
    text = clean_vtt(vtt_files[0].read_text(encoding="utf-8", errors="ignore"))
    # tidy up
    for f in vtt_files:
        try:
            f.unlink()
        except OSError:
            pass
    if not text:
        return None
    return Transcript(video_id=video_id, text=text, tool="yt-dlp+vtt-clean")


def clean_vtt(raw: str) -> str:
    """Strip WebVTT timestamps + dedupe rolling caption lines."""
    lines = raw.splitlines()
    out: list[str] = []
    seen_last = ""
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("WEBVTT") or s.startswith("Kind:") or s.startswith("Language:"):
            continue
        if "-->" in s:
            continue
        if re.fullmatch(r"\d+", s):  # cue index
            continue
        # inline VTT tags like <c> and timestamps <00:00:01.000>
        s = re.sub(r"<[^>]+>", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        if not s or s == seen_last:
            continue
        # dedupe rolling caption where next line == prev line + suffix
        if out and s.startswith(out[-1]):
            out[-1] = s
        else:
            out.append(s)
        seen_last = s
    return " ".join(out).strip()


def fetch_metadata(video_id: str) -> dict:
    """Get title / channel / date via yt-dlp --print (fast, no JSON parse)."""
    fmt = "%(title)s\t%(channel)s\t%(upload_date)s\t%(duration)s"
    try:
        r = subprocess.run(
            ["yt-dlp", "--skip-download", "--no-warnings", "--print", fmt,
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=60,
        )
        line = (r.stdout or "").strip().splitlines()[0] if r.stdout else ""
        if not line:
            return {"title": "", "channel": "", "publish_date": "", "duration": ""}
        parts = line.split("\t")
        while len(parts) < 4:
            parts.append("")
        title, channel, upload, dur = parts[:4]
        if len(upload) == 8 and upload.isdigit():
            upload = f"{upload[:4]}-{upload[4:6]}-{upload[6:]}"
        else:
            upload = ""
        duration_str = ""
        if dur.isdigit():
            n = int(dur)
            m, s = divmod(n, 60)
            h, m = divmod(m, 60)
            duration_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        return {
            "title": title,
            "channel": channel,
            "publish_date": upload,
            "duration": duration_str,
        }
    except Exception as e:
        print(f"  metadata error: {e}", file=sys.stderr)
    return {"title": "", "channel": "", "publish_date": "", "duration": ""}


def fetch_one(video_id: str, workdir: Path) -> Optional[Transcript]:
    for fn in (try_youtube_transcript_api, try_supadata):
        t = fn(video_id)
        if t and t.text:
            return t
    return try_ytdlp(video_id, workdir)


def write_markdown(
    author: str,
    t: Transcript,
    video_url: str,
    override_title: str = "",
) -> Path:
    author_dir = TRANSCRIPTS_ROOT / author
    author_dir.mkdir(parents=True, exist_ok=True)
    date = t.publish_date or time.strftime("%Y-%m-%d")
    title = override_title or t.title or t.video_id
    slug = slugify(title)
    path = author_dir / f"{date}-{slug}.md"
    body = (
        f"---\n"
        f"title: {title}\n"
        f"channel: {t.channel or ''}\n"
        f"video_url: {video_url}\n"
        f"publish_date: {t.publish_date or ''}\n"
        f"duration: {t.duration or ''}\n"
        f"date_fetched: {time.strftime('%Y-%m-%d')}\n"
        f"tool: {t.tool}\n"
        f"---\n\n"
        f"## Key takeaways\n"
        f"_TODO: 3–6 bullets after reading transcript._\n\n"
        f"## Transcript\n\n"
        f"{t.text}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--author", required=True, help="author slug, e.g. jason-bay")
    p.add_argument("--videos", required=True, help="path to list file")
    p.add_argument("--delay", type=float, default=2.0, help="seconds between videos")
    args = p.parse_args(argv)

    videos_path = Path(args.videos)
    if not videos_path.exists():
        print(f"video list not found: {videos_path}", file=sys.stderr)
        return 2

    workdir = REPO_ROOT / ".cache" / "yt-dlp"

    failures: list[tuple[str, str]] = []
    successes = 0

    for raw in videos_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split("|", 1)
        target = parts[0].strip()
        override = parts[1].strip() if len(parts) > 1 else ""

        vid = extract_video_id(target)
        if not vid:
            print(f"skip (bad id): {target}")
            failures.append((target, "bad id"))
            continue

        video_url = f"https://www.youtube.com/watch?v={vid}"
        print(f"[{args.author}] {vid}")

        t = fetch_one(vid, workdir)
        if not t:
            print("  FAILED all fallbacks")
            failures.append((video_url, "all fallbacks failed"))
            time.sleep(args.delay)
            continue

        meta = fetch_metadata(vid)
        t.title = t.title or meta["title"]
        t.channel = t.channel or meta["channel"]
        t.publish_date = t.publish_date or meta["publish_date"]
        t.duration = t.duration or meta["duration"]

        out = write_markdown(args.author, t, video_url, override)
        print(f"  wrote {out.relative_to(REPO_ROOT)}")
        successes += 1
        time.sleep(args.delay)

    print(f"\nDone: {successes} ok, {len(failures)} failed")
    if failures:
        print("Failures:")
        for url, reason in failures:
            print(f"  {url}  ({reason})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
