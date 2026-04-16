"""Reddit source — fetches today's new posts from AI subreddits via public JSON API."""
import logging
from datetime import date, datetime, timezone

import httpx

from .models import Article

logger = logging.getLogger(__name__)

# Each entry: (subreddit, category)
SUBREDDITS: list[tuple[str, str]] = [
    ("artificial", "AI"),
    ("MachineLearning", "AI"),
    ("LocalLLaMA", "AI"),
]

_MAX_POSTS_PER_SUB = 10
_MAX_CONTENT_CHARS = 3000
_HEADERS = {"User-Agent": "CavemanNewsBot/1.0 (github.com/cspoppuppy/caveman-news-local)"}


def fetch_reddit_articles(today: date | None = None) -> list[Article]:
    """Fetch Reddit posts published today (UTC) from configured subreddits."""
    if today is None:
        today = date.today()

    articles: list[Article] = []

    for subreddit, category in SUBREDDITS:
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=25"
        try:
            resp = httpx.get(url, headers=_HEADERS, timeout=15, follow_redirects=True, verify=False)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Failed to fetch r/%s: %s", subreddit, exc)
            continue

        count = 0
        for post in data.get("data", {}).get("children", []):
            if count >= _MAX_POSTS_PER_SUB:
                break

            p = post.get("data", {})

            created_utc = p.get("created_utc")
            if created_utc is None:
                continue
            pub_date = datetime.fromtimestamp(created_utc, tz=timezone.utc).date()
            if pub_date != today:
                continue

            title = p.get("title", "").strip()
            permalink = p.get("permalink", "")
            if not title or not permalink:
                continue

            content = (p.get("selftext") or "").strip()[:_MAX_CONTENT_CHARS]

            articles.append(Article(
                title=title,
                url=f"https://reddit.com{permalink}",
                content=content,
                source=f"r/{subreddit}",
                category=category,
                published_date=pub_date,
            ))
            count += 1

        logger.info("r/%s: fetched %d articles for %s", subreddit, count, today)

    return articles
