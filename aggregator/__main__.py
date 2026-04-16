import asyncio
import json
import logging
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from aggregator.llm import summarise
from aggregator.sources import fetch_reddit_articles, fetch_rss_articles, fetch_scraped_articles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SEEN_FILE = REPO_ROOT / ".seen_urls.json"
CONTENT_DIR = REPO_ROOT / "site" / "content"


def load_seen() -> set[str]:
    try:
        return set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()
    except Exception:
        return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2))


def git_push(filepaths: list[Path]) -> None:
    try:
        for fp in filepaths:
            subprocess.run(["git", "add", str(fp)], cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"🪨 caveman news {filepaths[0].stem}"],
            cwd=REPO_ROOT, check=True, capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.warning("Git failed: %s", e.stderr.decode() if e.stderr else e)


async def main() -> None:
    today = date.today()
    all_articles = fetch_rss_articles(today) + fetch_scraped_articles() + fetch_reddit_articles(today)

    seen = load_seen()
    new_articles = [a for a in all_articles if a.url and a.url not in seen]
    logger.info("%d new articles", len(new_articles))
    if not new_articles:
        return

    by_category: dict[str, dict[str, list]] = {}
    for a in new_articles:
        by_category.setdefault(a.category, {}).setdefault(a.source, []).append(a)

    newly_seen: set[str] = set()
    written: list[Path] = []

    for category, sources in sorted(by_category.items()):
        cat_slug = category.lower().replace(" ", "-")
        cat_dir = CONTENT_DIR / cat_slug
        cat_dir.mkdir(parents=True, exist_ok=True)

        index = cat_dir / "_index.md"
        if not index.exists():
            index.write_text(
                f'---\ntitle: "{category}"\ndescription: "Daily {category} news, caveman-style."\n---\n'
            )

        now = datetime.now(timezone.utc)
        content = (
            f'---\ntitle: "🪨 Caveman News — {today.strftime("%d %b %Y")}"\n'
            f'date: "{now.strftime("%Y-%m-%dT%H:%M:%SZ")}"\ndraft: false\n'
            f'tags: ["caveman", "digest", "{cat_slug}"]\ncategories: ["{category}"]\n---\n\n'
            f"*UGG BRING CAVE KNOWLEDGE. Sources: {', '.join(sorted(sources))}*\n\n"
        )
        count = 0
        for source, articles in sorted(sources.items()):
            content += f"## {source}\n\n"
            for article in articles:
                summary = await summarise(article.title, article.content)
                if summary is None:
                    continue
                content += f"### [{article.title}]({article.url})\n\n{summary}\n\n"
                newly_seen.add(article.url)
                count += 1

        if not count:
            continue
        out = cat_dir / f"{today.isoformat()}.md"
        out.write_text(content)
        written.append(out)
        logger.info("Written %s (%d articles)", out.name, count)

    if written:
        seen.update(newly_seen)
        save_seen(seen)
        git_push(written)


if __name__ == "__main__":
    asyncio.run(main())
