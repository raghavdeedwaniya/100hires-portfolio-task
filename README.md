# Cold Outreach Pipeline for B2B SaaS — Expert Content Corpus

A research repo collecting recent, high-signal content from 10 vetted practitioners on **cold outreach pipelines for B2B SaaS**. The corpus mixes YouTube/podcast transcripts, LinkedIn posts, and public guides/newsletters — organized so it can feed a real marketing playbook.

## The 10 experts

| # | Expert | Angle | One-line rationale |
|---|---|---|---|
| 1 | **Jason Bay** (Outbound Squad) | End-to-end outbound, cold calling frameworks | Coaches SDR/AE teams; 2026 podcast series still tactically deep |
| 2 | **Nick Cegelski & Armand Farrokh** (30MPC) | Tactical cold calling, discovery, objections | #1 actionable B2B sales podcast; sub-30-min rep-level episodes |
| 3 | **Josh Braun** (Sales DNA) | Cold email/call tone, "poke the bear" | Weekly YouTube uploads; canonical framework author |
| 4 | **Will Allred** (Lavender co-founder) | Cold email copywriting frameworks | LinkedIn teardowns backed by billions of analyzed sales emails |
| 5 | **Eric Nowoslawski** (Growth Engine X) | Clay + AI + tech stack | Clay's largest customer by enrichment volume; sends 4M+ emails/year |
| 6 | **Jed Mahrle** (Practical Prospecting) | Cold email + LinkedIn systems | Ex-PandaDoc; 30k Substack subs; 30% avg LinkedIn reply rate 2026 |
| 7 | **Florin Tatulea** (ZoomInfo, ex-Barrage) | Copy, sequencing, deliverability | LinkedIn Top Voice; 4x'd ARR + 20x'd outbound pipeline in-role |
| 8 | **Jay Feldman** (Lead Gen Jay) | Sending infra, AI cold email at scale | 84k YT subs; agency operator — inside view of a live cold-email op |
| 9 | **Elric Legloire** (Outbound Kitchen) | Outbound systems for $2M–$50M ARR SaaS | Same segment the corpus targets; 7 yrs / 24+ companies |
| 10 | **Alex Vacca** (ColdIQ co-founder) | Signal-based outbound, AI agents, Clay/Smartlead | $6M ARR agency; 2,200+ campaigns run |

Full rationales, links, and rejected candidates in [`research/sources.md`](research/sources.md).

**Angle coverage:** cold calling, cold email copywriting, deliverability/infra, Clay/AI/tech stack, list building/signals, outbound systems/ops, LinkedIn outbound — all covered by ≥2 of the 10.

## Methodology

1. **Vetting.** Built a 15–20 candidate pool from seed names + web search. Verified each is (a) a real practitioner running the motion, (b) publishing on-topic content within ~6 months, (c) has collectable content. Cut to 10 with complementary angles.
2. **YouTube transcripts.** Wrote `scripts/fetch_transcripts.py` — a fallback chain of `youtube-transcript-api` → Supadata API (key in `.env`, not committed) → `yt-dlp` auto-subs + VTT cleaner. 33 transcripts across 7 YouTube-active experts.
3. **LinkedIn posts.** Automated LinkedIn scraping is forbidden. Per-author scaffold files created; user completes manual paste per [`research/linkedin-posts/_INSTRUCTIONS.md`](research/linkedin-posts/_INSTRUCTIONS.md).
4. **Other assets.** Public newsletters, guides, and podcast episode pages fetched with `WebFetch`; only public/non-paywalled sources; each file cites source URL and fetch date.

## Repo map

```
README.md
.env                    # SUPADATA_API_KEY (gitignored)
.gitignore
research/
  sources.md            # vetted 10 + rejected pool + collection log
  linkedin-posts/
    _INSTRUCTIONS.md    # manual collection workflow
    <author>.md         # empty templates per author (10 files)
  youtube-transcripts/
    <author>/
      YYYY-MM-DD-<slug>.md   # metadata block + key takeaways + full transcript
  other/
    <author>/
      <slug>.md         # summarised public assets (newsletters, guides)
scripts/
  fetch_transcripts.py  # transcript fetcher (yta → Supadata → yt-dlp fallback)
  requirements.txt
  video-lists/          # per-author video ID lists
  README.md             # script usage
```

## Corpus size at handoff

- 33 YouTube/podcast transcripts (5 per author for 6 authors, 3 for Alex Vacca), 2025-01 to 2026-06
- All transcripts have "Key takeaways" bullets written after reading actual content
- 3 "other" documents (Jed Mahrle newsletter, ColdIQ guide, Jason Bay methodology episode)
- 10 LinkedIn scaffolds ready for manual paste (5 template posts each)

## Honest gaps & notes

- **LinkedIn is pending.** Automated LinkedIn access is against ToS and risks account bans; all LinkedIn content is user-collected per `_INSTRUCTIONS.md`. Prioritize: Will Allred, Jed Mahrle, Florin Tatulea, Alex Vacca (LinkedIn-first authors with no YouTube corpus).
- **`other/` is thin.** Fetched 3 pieces; more can be added if bandwidth allows (Josh Braun blog posts at joshbraun.com, Practical Prospecting archive, ColdIQ blog).
- **One 2024 Josh Braun video.** "Ditch the Pitch" (2024-10-13) predates the 6-month window but is included because it's the canonical framework post — cross-referenced by Braun's more recent content.
- **YouTube blocks.** Mid-run, `youtube-transcript-api` started returning IP-block errors; Supadata's API caught every one of them cleanly. No fetch was skipped. Logged in `sources.md`.
- **LinkedIn URL verification.** LinkedIn blocks automated fetching, so all `linkedin.com/in/*` links are flagged `[verify manually]` in `sources.md`.

## Next: from corpus to playbook

The playbook build should pattern-match across the 10 voices — where do they *agree* (converging tactics = high-confidence recommendations), and where do they *disagree* (edge cases to test)? Concrete cross-cuts to look for:

- Email volume caps per domain (20–30 vs 50–100 — deliverability discipline)
- Reply-rate benchmarks (3.4% avg vs 15–25% signal-based vs 30% LinkedIn)
- The role of Clay + AI vs personalization-by-hand
- Cold-calling openers that stack across 30MPC + Jason Bay + Josh Braun
