# scripts/

## fetch_transcripts.py

Pulls YouTube transcripts for the corpus. Tries, in order:

1. `youtube-transcript-api` (free, no key)
2. Supadata `/v1/youtube/transcript` (reads `SUPADATA_API_KEY` from `.env`)
3. `yt-dlp --write-auto-subs` → clean VTT

### Install
```bash
pip install -r scripts/requirements.txt
# yt-dlp also available as a standalone binary if pip install has issues
```

### Run
```bash
python scripts/fetch_transcripts.py \
    --author jason-bay \
    --videos scripts/video-lists/jason-bay.txt
```

`videos.txt` format — one entry per line:
```
<video_url_or_id>|<optional title override>
# comments and blank lines are ignored
https://www.youtube.com/watch?v=abcdefghijk | Jason Bay: 5 cold call openers
```

Files are written to `research/youtube-transcripts/<author>/<YYYY-MM-DD>-<slug>.md`
with a metadata block at the top. The "Key takeaways" section is a `TODO` —
fill it in after reading the transcript.

### Behavior
- Errors per-video: one broken video does not kill the run.
- 2-second default delay between videos.
- Failed videos are printed at the end so you can log them in `sources.md`.
