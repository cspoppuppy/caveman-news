"""Reddit source — fetches today's top posts from AI subreddits via public JSON API."""
import logging
from datetime import datetime, timezone

import httpx

from .models import Article

logger = logging.getLogger(__name__)

SUBREDDITS: list[tuple[str, str]] = [
    ("artificial", "AI"),
    ("MachineLearning", "AI"),
    ("LocalLLaMA", "AI"),
]

_MAX_POSTS = 5
_MAX_CHARS = 3000
_HEADERS = {"User-Agent": "CavemanNewsBot/1.0 (github.com/cspoppuppy/caveman-news)"}


def fetch_reddit_articles(since: datetime | None = None) -> list[Article]:
    since_ts = since.timestamp() if since else 0
    articles = []
    for sub, category in SUBREDDITS:
        try:
            resp = httpx.get(
                f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=25",
                headers=_HEADERS, timeout=15, follow_redirects=True, verify=False,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("r/%s failed: %s", sub, exc)
            continue
        posts = resp.json().get("data", {}).get("children", [])
        # already sorted by score desc; take top _MAX_POSTS with valid timestamps
        count = 0
        for post in posts:
            if count >= _MAX_POSTS:
                break
            p = post["data"]
            ts = p.get("created_utc")
            if not ts or ts < since_ts:
                continue
            title, perm = p.get("title", "").strip(), p.get("permalink", "")
            if not title or not perm:
                continue
            pub_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            articles.append(Article(
                title=title, url=f"https://reddit.com{perm}",
                content=(p.get("selftext") or "")[:_MAX_CHARS],
                source=f"r/{sub}", category=category, published_at=pub_dt,
            ))
            count += 1
        logger.info("r/%s: %d articles", sub, count)
    return articles
