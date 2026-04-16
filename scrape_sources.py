"""Web scraping sources for caveman-news-local.

Scrapes articles from sites that have no public RSS feed:
  - Anthropic (https://www.anthropic.com/news)
  - Mistral   (https://mistral.ai/news/)
"""
import logging

import httpx
from bs4 import BeautifulSoup

from rss_sources import Article

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CavemanNewsBot/1.0)"}
_MAX_ARTICLES = 5
_MAX_CONTENT_CHARS = 3000


def _extract_article_text(html: str) -> str:
    """Extract readable text from an article page."""
    soup = BeautifulSoup(html, "lxml")
    for candidate in ("article", "main"):
        tag = soup.find(candidate)
        if tag:
            return tag.get_text(" ", strip=True)[:_MAX_CONTENT_CHARS]
    # Fallback: any div whose class contains "content"
    for div in soup.find_all("div", class_=True):
        classes = " ".join(div.get("class", []))
        if "content" in classes.lower():
            text = div.get_text(" ", strip=True)
            if len(text) > 200:
                return text[:_MAX_CONTENT_CHARS]
    return ""


def _fetch_anthropic() -> list[Article]:
    """Scrape up to 5 articles from https://www.anthropic.com/news."""
    base_url = "https://www.anthropic.com"
    index_url = f"{base_url}/news"
    articles: list[Article] = []

    try:
        resp = httpx.get(index_url, timeout=15, follow_redirects=True, headers=_HEADERS, verify=False)
        if resp.status_code != 200:
            logger.warning("Anthropic news returned HTTP %d", resp.status_code)
            return []
    except Exception as exc:
        logger.warning("Failed to fetch Anthropic news index: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    seen: set[str] = set()
    links: list[tuple[str, str]] = []  # (href, title)

    for a_tag in soup.find_all("a", href=True):
        href: str = a_tag["href"]
        if not href.startswith("/news/"):
            continue
        # Skip the index page itself
        if href.rstrip("/") == "/news":
            continue
        if href in seen:
            continue
        seen.add(href)

        # Try to get a meaningful title from the link text or a nearby heading
        title = a_tag.get_text(" ", strip=True)
        if not title:
            for heading_tag in ("h2", "h3", "h1"):
                heading = a_tag.find(heading_tag)
                if heading:
                    title = heading.get_text(" ", strip=True)
                    break
        if not title:
            # Walk up to parent and look for headings
            parent = a_tag.parent
            if parent:
                for heading_tag in ("h2", "h3", "h1"):
                    heading = parent.find(heading_tag)
                    if heading:
                        title = heading.get_text(" ", strip=True)
                        break

        if title:
            links.append((href, title))

        if len(links) >= _MAX_ARTICLES:
            break

    for href, title in links:
        article_url = f"{base_url}{href}"
        content = ""
        try:
            art_resp = httpx.get(article_url, timeout=10, follow_redirects=True, headers=_HEADERS, verify=False)
            if art_resp.status_code == 200:
                content = _extract_article_text(art_resp.text)
        except Exception as exc:
            logger.warning("Failed to fetch Anthropic article %s: %s", article_url, exc)

        articles.append(Article(title=title, url=article_url, content=content, source="Anthropic", category="AI"))

    return articles


def _fetch_mistral() -> list[Article]:
    """Scrape up to 5 articles from https://mistral.ai/news/."""
    base_url = "https://mistral.ai"
    index_url = f"{base_url}/news/"
    articles: list[Article] = []

    try:
        resp = httpx.get(index_url, timeout=15, follow_redirects=True, headers=_HEADERS, verify=False)
        if resp.status_code != 200:
            logger.warning("Mistral news returned HTTP %d", resp.status_code)
            return []
    except Exception as exc:
        logger.warning("Failed to fetch Mistral news index: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    seen: set[str] = set()
    links: list[tuple[str, str]] = []

    for a_tag in soup.find_all("a", href=True):
        href: str = a_tag["href"]
        if not (href.startswith("/news/") or href.startswith("/en/news/")):
            continue
        if href in seen:
            continue
        seen.add(href)

        title = a_tag.get_text(" ", strip=True)
        if not title:
            for heading_tag in ("h2", "h3", "h1"):
                heading = a_tag.find(heading_tag)
                if heading:
                    title = heading.get_text(" ", strip=True)
                    break
        if not title:
            parent = a_tag.parent
            if parent:
                for heading_tag in ("h2", "h3", "h1"):
                    heading = parent.find(heading_tag)
                    if heading:
                        title = heading.get_text(" ", strip=True)
                        break

        if title:
            links.append((href, title))

        if len(links) >= _MAX_ARTICLES:
            break

    for href, title in links:
        article_url = f"{base_url}{href}"
        content = ""
        try:
            art_resp = httpx.get(article_url, timeout=10, follow_redirects=True, headers=_HEADERS, verify=False)
            if art_resp.status_code == 200:
                content = _extract_article_text(art_resp.text)
        except Exception as exc:
            logger.warning("Failed to fetch Mistral article %s: %s", article_url, exc)

        articles.append(Article(title=title, url=article_url, content=content, source="Mistral", category="AI"))

    return articles


def fetch_scraped_articles() -> list[Article]:
    """Scrape articles from Anthropic and Mistral news pages.

    Each source is independently try/except'd — failures are logged and
    the function continues with remaining sources. Never crashes.

    Returns:
        A flat list of Article objects from all scraped sources.
    """
    articles: list[Article] = []

    try:
        anthropic_articles = _fetch_anthropic()
        articles.extend(anthropic_articles)
        logger.info("Anthropic: fetched %d articles", len(anthropic_articles))
    except Exception as exc:
        logger.warning("Anthropic scraper failed unexpectedly: %s", exc)

    try:
        mistral_articles = _fetch_mistral()
        articles.extend(mistral_articles)
        logger.info("Mistral: fetched %d articles", len(mistral_articles))
    except Exception as exc:
        logger.warning("Mistral scraper failed unexpectedly: %s", exc)

    return articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_scraped_articles()

    from collections import Counter
    counts = Counter(a.source for a in results)
    for source in ("Anthropic", "Mistral"):
        print(f"{source}: {counts.get(source, 0)} articles")
    print(f"\nTotal: {len(results)} articles")
