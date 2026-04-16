"""Web scraping sources — Anthropic and Mistral (no public RSS feed)."""
import logging

import httpx
from bs4 import BeautifulSoup

from .models import Article

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CavemanNewsBot/1.0)"}
_MAX_ARTICLES = 5
_MAX_CONTENT_CHARS = 3000


def _extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for candidate in ("article", "main"):
        tag = soup.find(candidate)
        if tag:
            return tag.get_text(" ", strip=True)[:_MAX_CONTENT_CHARS]
    for div in soup.find_all("div", class_=True):
        classes = " ".join(div.get("class", []))
        if "content" in classes.lower():
            text = div.get_text(" ", strip=True)
            if len(text) > 200:
                return text[:_MAX_CONTENT_CHARS]
    return ""


def _scrape_links(soup, path_prefix: str) -> list[tuple[str, str]]:
    """Extract (href, title) pairs whose href starts with path_prefix."""
    seen: set[str] = set()
    links: list[tuple[str, str]] = []

    for a_tag in soup.find_all("a", href=True):
        href: str = a_tag["href"]
        if not href.startswith(path_prefix):
            continue
        if href.rstrip("/") == path_prefix.rstrip("/"):
            continue
        if href in seen:
            continue
        seen.add(href)

        title = a_tag.get_text(" ", strip=True)
        if not title:
            for tag in ("h2", "h3", "h1"):
                heading = a_tag.find(tag) or (a_tag.parent and a_tag.parent.find(tag))
                if heading:
                    title = heading.get_text(" ", strip=True)
                    break

        if title:
            links.append((href, title))

        if len(links) >= _MAX_ARTICLES:
            break

    return links


def _fetch_source(base_url: str, index_url: str, path_prefix: str, source_name: str) -> list[Article]:
    articles: list[Article] = []

    try:
        resp = httpx.get(index_url, timeout=15, follow_redirects=True, headers=_HEADERS, verify=False)
        if resp.status_code != 200:
            logger.warning("%s news returned HTTP %d", source_name, resp.status_code)
            return []
    except Exception as exc:
        logger.warning("Failed to fetch %s news index: %s", source_name, exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    for href, title in _scrape_links(soup, path_prefix):
        article_url = f"{base_url}{href}"
        content = ""
        try:
            art_resp = httpx.get(article_url, timeout=10, follow_redirects=True, headers=_HEADERS, verify=False)
            if art_resp.status_code == 200:
                content = _extract_article_text(art_resp.text)
        except Exception as exc:
            logger.warning("Failed to fetch %s article %s: %s", source_name, article_url, exc)

        articles.append(Article(title=title, url=article_url, content=content, source=source_name, category="AI"))

    return articles


def fetch_scraped_articles() -> list[Article]:
    """Scrape Anthropic and Mistral. Each source is independently guarded — never crashes."""
    articles: list[Article] = []

    for name, base, index, prefix in [
        ("Anthropic", "https://www.anthropic.com", "https://www.anthropic.com/news", "/news/"),
        ("Mistral", "https://mistral.ai", "https://mistral.ai/news/", "/news/"),
    ]:
        try:
            fetched = _fetch_source(base, index, prefix, name)
            articles.extend(fetched)
            logger.info("%s: fetched %d articles", name, len(fetched))
        except Exception as exc:
            logger.warning("%s scraper failed unexpectedly: %s", name, exc)

    return articles
