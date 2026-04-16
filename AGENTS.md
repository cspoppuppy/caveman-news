# AGENTS.md — Conventions for AI Agents

## Documentation

**Always keep docs up to date.**
- After any code change: update `README.md` if public interface, CLI usage, or setup steps changed.
- After any config change (cron, sources, LLM, paths): reflect in `README.md`.
- After adding/removing sources: update source list in `README.md`.
- Do not leave stale comments, outdated examples, or incorrect instructions.

## Architecture

- Hugo site lives under `site/`. Content written to `site/content/ai/YYYY-MM-DD.md`.
- Aggregator is a Python package under `aggregator/`. Entry point: `aggregator/__main__.py`.
- Git push is handled by `run.sh`, not by Python code.
- `.seen_urls.json` and `.last_run` are local state — gitignored.
- LLM calls use GitHub Copilot SDK (`gpt-5-mini`). No API key required.

## Conventions

- Caveman-speak summaries generated via caveman skill at `/Users/sha.cheng/.copilot/installed-plugins/caveman/caveman/skills/caveman/SKILL.md`.
- Same-day reruns append to existing `.md` file; seen-URL dedup prevents duplicate articles.
- Time window: articles from `last_run` to `now`. Default (no `.last_run`): start of today UTC.
