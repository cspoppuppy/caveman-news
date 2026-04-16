"""Reddit source — fetches posts since last run from AI subreddits via public JSON API."""
import logging
from datetime import date, datetime, timezone

import httpx

from .models import Article

logger = logging.getLogger(__name__)

SUBREDDITS: list[tuple[str, str]] = [
    ("artificial", "AI"),
    ("MachineLearning", "AI"),
    ("LocalLLaMA", "AI"),
]

_MAX_POSTS = 10
_MAX_CHARS = 3000
_HEADERS = {"User-Agent": "CavemanNewsBot/1.0 (github.com/cspoppuppy/caveman-news)"}


def fetch_reddit_articles(since: datetime | None = None) -> list[Article]:
    if since is None:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    since_ts = since.timestamp()
    articles = []
    for sub, category in SUBREDDITS:
        try:
            resp = httpx.get(
                f"https://www.reddit.com/r/{sub}/new.json?limit=25",
                headers=_HEADERS, timeout=15, follow_redirects=True, verify=False,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("r/%s failed: %s", sub, exc)
            continue
        count = 0
        for post in resp.json().get("data", {}).get("children", []):
            if count >= _MAX_POSTS:
                break
            p = post["data"]
            ts = p.get("created_utc")
            if not ts or ts < since_ts:
                continue
            title, perm = p.get("title", "").strip(), p.get("permalink", "")
            if not title or not perm:
                continue
            pub_date = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            articles.append(Article(
                title=title, url=f"https://reddit.com{perm}",
                content=(p.get("selftext") or "")[:_MAX_CHARS],
                source=f"r/{sub}", category=category, published_date=pub_date,
            ))
            count += 1
        logger.info("r/%s: %d articles", sub, count)
    return articles
