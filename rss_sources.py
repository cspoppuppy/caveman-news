import re
import logging
from dataclasses import dataclass

import feedparser

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    url: str
    content: str
    source: str


RSS_FEEDS: list[tuple[str, str]] = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("GitHub Copilot", "https://github.blog/feed/?category=ai"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("HuggingFace", "https://huggingface.co/blog/feed.xml"),
    ("The Verge AI", "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
]

_MAX_ENTRIES_PER_FEED = 5
_MAX_CONTENT_CHARS = 3000


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def fetch_rss_articles() -> list[Article]:
    articles: list[Article] = []

    for source_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as exc:
            logger.warning("Failed to fetch RSS feed %s (%s): %s", source_name, feed_url, exc)
            continue

        for entry in feed.entries[:_MAX_ENTRIES_PER_FEED]:
            title = entry.get("title", "")
            url = entry.get("link", "")

            if not title or not url:
                continue

            raw_content = entry.get("summary", "") or entry.get("description", "")
            content = _strip_html(raw_content)[:_MAX_CONTENT_CHARS]

            articles.append(Article(title=title, url=url, content=content, source=source_name))

    return articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_rss_articles()

    from collections import Counter

    counts = Counter(a.source for a in results)
    for source_name, _ in RSS_FEEDS:
        print(f"{source_name}: {counts.get(source_name, 0)} articles")
    print(f"\nTotal: {len(results)} articles")
