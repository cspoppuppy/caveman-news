import re
import logging
from dataclasses import dataclass, field
from datetime import date

import feedparser

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    url: str
    content: str
    source: str
    category: str = "AI"
    published_date: date | None = field(default=None, compare=False)


# Each entry: (source_name, feed_url, category)
RSS_FEEDS: list[tuple[str, str, str]] = [
    ("OpenAI", "https://openai.com/news/rss.xml", "AI"),
    ("GitHub Copilot", "https://github.blog/feed/?category=ai", "AI"),
    ("Google AI", "https://blog.google/technology/ai/rss/", "AI"),
    ("HuggingFace", "https://huggingface.co/blog/feed.xml", "AI"),
    ("The Verge AI", "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "AI"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "AI"),
]

_MAX_ENTRIES_PER_FEED = 10  # scan more; date filter will trim
_MAX_CONTENT_CHARS = 3000


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def fetch_rss_articles(today: date | None = None) -> list[Article]:
    """Fetch RSS articles published today (UTC). Pass today=None to use date.today()."""
    if today is None:
        today = date.today()

    articles: list[Article] = []

    for source_name, feed_url, category in RSS_FEEDS:
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

            # Date filter: only today's articles
            pub = entry.get("published_parsed")
            if pub:
                pub_date = date(*pub[:3])  # (year, month, day) from struct_time
                if pub_date != today:
                    continue
            else:
                # No date metadata — include (better than silently missing)
                pub_date = None

            raw_content = entry.get("summary", "") or entry.get("description", "")
            content = _strip_html(raw_content)[:_MAX_CONTENT_CHARS]

            articles.append(Article(
                title=title,
                url=url,
                content=content,
                source=source_name,
                category=category,
                published_date=pub_date,
            ))

    return articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_rss_articles()

    from collections import Counter

    counts = Counter(a.source for a in results)
    for source_name, _ in RSS_FEEDS:
        print(f"{source_name}: {counts.get(source_name, 0)} articles")
    print(f"\nTotal: {len(results)} articles")
