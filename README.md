# 🪨 Caveman News Local

> UGG AGGREGATE AI NEWS. UGG TRANSLATE TO CAVE SPEAK. UGG WRITE FILE. EVERY DAY.

## What it does

Caveman News Local is a daily AI news aggregator that runs entirely on your machine:

- **Fetches** AI news from **8 sources** — 6 RSS feeds + 2 scraped sites:
  | Source | Type |
  |---|---|
  | OpenAI | RSS |
  | GitHub Copilot | RSS |
  | Google AI | RSS |
  | HuggingFace | RSS |
  | The Verge AI | RSS |
  | VentureBeat AI | RSS |
  | Anthropic | Scraped (`anthropic.com/news`) |
  | Mistral | Scraped (`mistral.ai/news/`) |
- **Translates** each article to caveman-speak using the GitHub Copilot SDK (`gpt-5-mini`)
- **Writes** a single `news/YYYY-MM-DD-HH-MM-SS.md` file per run (all sources combined)
- **Auto git commits** and pushes the output file
- **Runs daily at 9:30am** via macOS crontab

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager (`brew install uv`)
- A GitHub Copilot subscription (free tier works)
- Authenticated via `gh auth login` **or** the Copilot CLI already logged in
- `git` configured with push access to the repo remote

## Setup

```bash
git clone <this-repo> caveman-news-local
cd caveman-news-local
uv sync                  # installs all deps including github-copilot-sdk
bash setup_cron.sh       # installs the 9:30am cron job
```

> **No API keys or `.env` file needed** — the script uses your existing Copilot login credentials automatically via the `CopilotClient` SDK.

## Run manually

```bash
uv run python fetch.py
```

## Output format

Each run produces one file in `news/`, named by timestamp (e.g. `news/2025-04-15-09-30-00.md`):

```markdown
# 🪨 Caveman News — 2025-04-15 09:30:00

> UGG BRING NEWS. 23 NEW THING HAPPEN. READ OR NO READ. UGG NOT CARE.

## OpenAI
### GPT-5 released
🔗 https://openai.com/news/gpt-5
UGH. BIG BRAIN FIRE. OPENAI MAKE NEW THING. GPT-5. VERY SMART. UGG SCARED. MANY STONE.

## Anthropic
...
```

Articles are grouped by source and written sequentially. Each article shows title, link, and a ≤120-word caveman-speak summary.

## Project structure

```
caveman-news-local/
├── fetch.py              ← Run this
├── rss_sources.py        ← 6 RSS feeds
├── scrape_sources.py     ← 2 scraped sites (Anthropic, Mistral)
├── llm.py                ← GitHub Copilot SDK summariser (gpt-5-mini)
├── setup_cron.sh         ← Install cron job
├── pyproject.toml
├── news/                 ← Output markdown files (git tracked)
└── logs/                 ← cron.log lives here (gitignored)
```

## Cron management

```bash
# Install (idempotent — safe to run multiple times):
bash setup_cron.sh

# Check installed jobs:
crontab -l

# Remove:
crontab -l | grep -v "caveman-news-local" | crontab -

# View logs:
tail -f logs/cron.log
```

`setup_cron.sh` resolves the absolute path to `uv` at install time and writes a cron line like:

```
30 9 * * * cd "/path/to/caveman-news-local" && "/usr/local/bin/uv" run python fetch.py >> "/path/to/logs/cron.log" 2>&1
```

The `logs/` directory is created automatically by the script if it does not exist.

## Deduplication

Articles are deduplicated via `.seen_urls.json` (gitignored). On each run, only URLs not already recorded in this file are fetched, summarised, and written. Delete `.seen_urls.json` to re-fetch all articles from scratch.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ImportError: copilot` | Run `uv sync` to install `github-copilot-sdk` |
| `[UGH. UGG NO GET SUMMARY. BRAIN HURT.]` in output | Ensure you have a GitHub Copilot subscription and are logged in (`gh auth login`) |
| Cron not running | Check `crontab -l` — run `bash setup_cron.sh` if the entry is missing |
| Cron runs but no output | Check `logs/cron.log` for errors |
| RSS feed empty | Source may be temporarily down — script continues gracefully with remaining sources |
| Git push fails | Ensure remote is configured: `git remote -v` |

## Adding/removing sources

- **RSS feeds** — edit the `RSS_FEEDS` list in `rss_sources.py`
- **Scraped sites** — add a new `_fetch_<source>()` function in `scrape_sources.py` and call it from `fetch_scraped_articles()`
