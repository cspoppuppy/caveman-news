import asyncio
import json
import logging
import subprocess
from datetime import date, datetime
from pathlib import Path

from rss_sources import fetch_rss_articles
from scrape_sources import fetch_scraped_articles
from reddit_sources import fetch_reddit_articles
from llm import summarise

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent
SEEN_URLS_FILE = REPO_ROOT / ".seen_urls.json"
CONTENT_DIR = REPO_ROOT / "content"


def load_seen_urls() -> set[str]:
    if SEEN_URLS_FILE.exists():
        try:
            return set(json.loads(SEEN_URLS_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_seen_urls(seen: set[str]) -> None:
    SEEN_URLS_FILE.write_text(json.dumps(sorted(seen), indent=2))


def git_commit_and_push(filepaths: list[Path]) -> None:
    try:
        for fp in filepaths:
            subprocess.run(["git", "add", str(fp)], cwd=REPO_ROOT, check=True, capture_output=True)
        commit_msg = f"🪨 caveman news {filepaths[0].stem}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True, capture_output=True)
        logger.info("Git: committed and pushed %d file(s)", len(filepaths))
    except subprocess.CalledProcessError as e:
        logger.warning("Git operation failed: %s\n%s", e, e.stderr.decode() if e.stderr else "")


async def main() -> None:
    logger.info("=== Caveman News starting ===")
    today = date.today()

    # 1. Fetch all articles
    logger.info("Fetching RSS articles (today: %s)...", today)
    rss_articles = fetch_rss_articles(today=today)
    logger.info("Fetched %d RSS articles", len(rss_articles))

    logger.info("Fetching scraped articles...")
    scraped_articles = fetch_scraped_articles()
    logger.info("Fetched %d scraped articles", len(scraped_articles))

    logger.info("Fetching Reddit articles (today: %s)...", today)
    reddit_articles = fetch_reddit_articles(today=today)
    logger.info("Fetched %d Reddit articles", len(reddit_articles))

    all_articles = rss_articles + scraped_articles + reddit_articles

    # 2. Deduplicate
    seen_urls = load_seen_urls()
    new_articles = [a for a in all_articles if a.url and a.url not in seen_urls]
    logger.info("%d new articles after dedup (skipped %d)", len(new_articles), len(all_articles) - len(new_articles))

    if not new_articles:
        logger.info("No new articles. Nothing to write.")
        return

    # 3. Group by category → source
    by_category: dict[str, dict[str, list]] = {}
    for article in new_articles:
        by_category.setdefault(article.category, {}).setdefault(article.source, []).append(article)

    # 4. Build Hugo content files — one per category
    all_newly_seen: set[str] = set()
    written_files: list[Path] = []

    for category, sources in sorted(by_category.items()):
        cat_slug = category.lower().replace(" ", "-")
        cat_dir = CONTENT_DIR / cat_slug
        cat_dir.mkdir(parents=True, exist_ok=True)

        # Ensure category _index.md exists
        index_file = cat_dir / "_index.md"
        if not index_file.exists():
            index_file.write_text(
                f'---\ntitle: "{category}"\ndescription: "Daily {category} news, caveman-style."\n---\n',
                encoding="utf-8",
            )

        output_path = cat_dir / f"{today.isoformat()}.md"
        sources_used = sorted(sources.keys())
        now = datetime.utcnow()

        lines = [
            "---",
            f'title: "🪨 Caveman News — {today.strftime("%d %b %Y")}"',
            f'date: "{now.strftime("%Y-%m-%dT%H:%M:%SZ")}"',
            "draft: false",
            f'tags: ["caveman", "digest", "{cat_slug}"]',
            f'categories: ["{category}"]',
            "---",
            "",
            f"*UGG BRING CAVE KNOWLEDGE. Sources: {', '.join(sources_used)}*",
            "",
        ]

        newly_seen_cat: set[str] = set()
        total_summarised = 0

        for source, articles in sorted(sources.items()):
            lines.append(f"## {source}")
            lines.append("")
            for article in articles:
                logger.info("Summarising: [%s / %s] %s", category, source, article.title[:55])
                summary = await summarise(article.title, article.content)
                if summary is None:
                    logger.info("Skipping (no summary): %s", article.title[:60])
                    continue
                lines.append(f"### [{article.title}]({article.url})")
                lines.append("")
                lines.append(summary)
                lines.append("")
                newly_seen_cat.add(article.url)
                total_summarised += 1

        if total_summarised == 0:
            logger.info("No summaries for category %s. Skipping.", category)
            continue

        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Written: %s (%d articles)", output_path, total_summarised)
        all_newly_seen.update(newly_seen_cat)
        written_files.append(output_path)

    # 5. Save seen URLs + git push
    if not written_files:
        logger.info("Nothing written. UGG BORED.")
        return

    seen_urls.update(all_newly_seen)
    save_seen_urls(seen_urls)
    git_commit_and_push(written_files)

    logger.info("=== Caveman News done. UGG PLEASED. ===")


if __name__ == "__main__":
    asyncio.run(main())
