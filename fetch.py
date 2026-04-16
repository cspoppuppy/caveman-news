import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from rss_sources import fetch_rss_articles
from scrape_sources import fetch_scraped_articles
from llm import summarise

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent
SEEN_URLS_FILE = REPO_ROOT / ".seen_urls.json"
NEWS_DIR = REPO_ROOT / "news"


def load_seen_urls() -> set[str]:
    if SEEN_URLS_FILE.exists():
        try:
            return set(json.loads(SEEN_URLS_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_seen_urls(seen: set[str]) -> None:
    SEEN_URLS_FILE.write_text(json.dumps(sorted(seen), indent=2))


def git_commit_and_push(filepath: Path) -> None:
    try:
        subprocess.run(["git", "add", str(filepath)], cwd=REPO_ROOT, check=True, capture_output=True)
        commit_msg = f"🪨 caveman news {filepath.stem}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True, capture_output=True)
        logger.info("Git: committed and pushed %s", filepath.name)
    except subprocess.CalledProcessError as e:
        logger.warning("Git operation failed: %s\n%s", e, e.stderr.decode() if e.stderr else "")


async def main() -> None:
    logger.info("=== Caveman News starting ===")

    # 1. Fetch all articles
    logger.info("Fetching RSS articles...")
    rss_articles = fetch_rss_articles()
    logger.info("Fetched %d RSS articles", len(rss_articles))

    logger.info("Fetching scraped articles...")
    scraped_articles = fetch_scraped_articles()
    logger.info("Fetched %d scraped articles", len(scraped_articles))

    all_articles = rss_articles + scraped_articles

    # 2. Deduplicate
    seen_urls = load_seen_urls()
    new_articles = [a for a in all_articles if a.url and a.url not in seen_urls]
    logger.info("%d new articles after dedup (skipped %d)", len(new_articles), len(all_articles) - len(new_articles))

    if not new_articles:
        logger.info("No new articles. Nothing to write.")
        return

    # 3. Summarise each article
    # Group by source for the markdown output
    by_source: dict[str, list[tuple]] = {}
    for article in new_articles:
        if article.source not in by_source:
            by_source[article.source] = []
        by_source[article.source].append(article)

    # 4. Build markdown content
    now = datetime.now()
    filename = now.strftime("%Y-%m-%d-%H-%M-%S") + ".md"
    output_path = NEWS_DIR / filename

    lines = [
        f"# 🪨 Caveman News — {now.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"> UGG BRING NEWS. {len(new_articles)} NEW THING HAPPEN. READ OR NO READ. UGG NOT CARE.",
        "",
    ]

    total_summarised = 0
    newly_seen: set[str] = set()

    for source, articles in by_source.items():
        lines.append(f"## {source}")
        lines.append("")
        for article in articles:
            logger.info("Summarising: [%s] %s", source, article.title[:60])
            summary = await summarise(article.title, article.content)
            lines.append(f"### {article.title}")
            lines.append(f"🔗 {article.url}")
            lines.append("")
            lines.append(summary)
            lines.append("")
            newly_seen.add(article.url)
            total_summarised += 1

    # 5. Write file
    NEWS_DIR.mkdir(exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Written: %s (%d articles)", output_path.name, total_summarised)

    # 6. Update seen URLs (only after successful write)
    seen_urls.update(newly_seen)
    save_seen_urls(seen_urls)

    # 7. Git commit + push
    git_commit_and_push(output_path)

    logger.info("=== Caveman News done. UGG PLEASED. ===")


if __name__ == "__main__":
    asyncio.run(main())
