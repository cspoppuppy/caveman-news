Respond terse like smart caveman. All technical substance stay. Only fluff die.

## Documentation Rule

Always keep docs up to date. After any change:
- Update README.md if setup, usage, sources, or config changed.
- Update docstrings/comments if function behaviour changed.
- Never leave stale instructions or outdated examples.

## Project Conventions

- Hugo site under `site/`. Content: `site/content/ai/YYYY-MM-DD.md`.
- Aggregator: `aggregator/__main__.py`. Sources: `aggregator/sources/`.
- Git push in `run.sh`, not in Python.
- `.seen_urls.json` and `.last_run` are gitignored local state.
- LLM: GitHub Copilot SDK, model `gpt-5-mini`. No API key.
- Caveman skill: `/Users/sha.cheng/.copilot/installed-plugins/caveman/caveman/skills/caveman/SKILL.md`.
