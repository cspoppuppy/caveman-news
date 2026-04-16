"""Reddit source — fetches today's new posts from AI subreddits via public JSON API."""
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


def fetch_reddit_articles(today: date | None = None) -> list[Article]:
    today = today or date.today()
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
            if not ts or datetime.fromtimestamp(ts, tz=timezone.utc).date() != today:
                continue
            title, perm = p.get("title", "").strip(), p.get("permalink", "")
            if not title or not perm:
                continue
            articles.append(Article(
                title=title, url=f"https://reddit.com{perm}",
                content=(p.get("selftext") or "")[:_MAX_CHARS],
                source=f"r/{sub}", category=category, published_date=today,
            ))
            count += 1
        logger.info("r/%s: %d articles", sub, count)
    return articles
