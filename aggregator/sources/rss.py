import re
import logging
from datetime import datetime, timezone

import feedparser

from .models import Article

logger = logging.getLogger(__name__)

RSS_FEEDS: list[tuple[str, str, str]] = [
    ("OpenAI", "https://openai.com/news/rss.xml", "AI"),
    ("GitHub Copilot", "https://github.blog/feed/?category=ai", "AI"),
    ("Google AI", "https://blog.google/technology/ai/rss/", "AI"),
    ("HuggingFace", "https://huggingface.co/blog/feed.xml", "AI"),
    ("The Verge AI", "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "AI"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "AI"),
    ("The Register AI", "https://www.theregister.com/science/ai/headlines.atom", "AI"),
]

_MAX_ENTRIES = 10
_MAX_CHARS = 3000


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def fetch_rss_articles(since: datetime | None = None) -> list[Article]:
    if since is None:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    articles = []
    for source, url, category in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as exc:
            logger.warning("RSS %s failed: %s", source, exc)
            continue
        for entry in feed.entries[:_MAX_ENTRIES]:
            title, link = entry.get("title", ""), entry.get("link", "")
            if not title or not link:
                continue
            pub = entry.get("published_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < since:
                    continue
            content = _strip_html(entry.get("summary", "") or entry.get("description", ""))[:_MAX_CHARS]
            articles.append(Article(
                title=title, url=link, content=content, source=source, category=category,
                published_at=pub_dt if pub else None,
            ))
    return articles
