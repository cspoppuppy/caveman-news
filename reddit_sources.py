"""Reddit source for caveman-news-local.

Fetches today's top new posts from AI-focused subreddits via the public JSON API.
No auth or API key required.
"""
import logging
from datetime import date, datetime, timezone

import httpx

from rss_sources import Article

logger = logging.getLogger(__name__)

# Each entry: (subreddit, category)
# Add new subreddits here — category controls markdown grouping
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

            # Filter: today only (UTC)
            created_utc = p.get("created_utc")
            if created_utc is None:
                continue
            pub_date = datetime.fromtimestamp(created_utc, tz=timezone.utc).date()
            if pub_date != today:
                continue

            title = p.get("title", "").strip()
            permalink = p.get("permalink", "")
            post_url = p.get("url") or f"https://reddit.com{permalink}"

            if not title or not permalink:
                continue

            # Prefer selftext body; fallback to title for link posts
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_reddit_articles()
    from collections import Counter
    counts = Counter(a.source for a in results)
    for sub, _ in SUBREDDITS:
        print(f"r/{sub}: {counts.get(f'r/{sub}', 0)} posts")
    print(f"\nTotal: {len(results)} posts")
