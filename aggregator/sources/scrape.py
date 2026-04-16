"""Web scraping sources — Anthropic and Mistral (no public RSS feed)."""
import logging

import httpx
from bs4 import BeautifulSoup

from .models import Article

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CavemanNewsBot/1.0)"}
_MAX_ARTICLES = 5
_MAX_CHARS = 3000

SCRAPED_SOURCES = [
    ("Anthropic", "https://www.anthropic.com", "https://www.anthropic.com/news", "/news/"),
    ("Mistral",   "https://mistral.ai",         "https://mistral.ai/news/",       "/news/"),
]


def _text(tag) -> str:
    return tag.get_text(" ", strip=True) if tag else ""


def _article_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for sel in ("article", "main"):
        if tag := soup.find(sel):
            return _text(tag)[:_MAX_CHARS]
    for div in soup.find_all("div", class_=True):
        if "content" in " ".join(div.get("class", [])).lower():
            if len(t := _text(div)) > 200:
                return t[:_MAX_CHARS]
    return ""


def _scrape_links(soup, prefix: str) -> list[tuple[str, str]]:
    seen, links = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith(prefix) or href.rstrip("/") == prefix.rstrip("/") or href in seen:
            continue
        seen.add(href)
        title = _text(a) or next(
            (_text(h) for scope in (a, a.parent) if scope
             for tag in ("h2", "h3", "h1") if (h := scope.find(tag))), ""
        )
        if title:
            links.append((href, title))
        if len(links) >= _MAX_ARTICLES:
            break
    return links


def _fetch_source(name: str, base: str, index_url: str, prefix: str) -> list[Article]:
    try:
        resp = httpx.get(index_url, timeout=15, follow_redirects=True, headers=_HEADERS, verify=False)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("%s index failed: %s", name, exc)
        return []
    articles = []
    for href, title in _scrape_links(BeautifulSoup(resp.text, "lxml"), prefix):
        content = ""
        try:
            r = httpx.get(f"{base}{href}", timeout=10, follow_redirects=True, headers=_HEADERS, verify=False)
            if r.status_code == 200:
                content = _article_text(r.text)
        except Exception as exc:
            logger.warning("%s article failed %s: %s", name, href, exc)
        articles.append(Article(title=title, url=f"{base}{href}", content=content, source=name, category="AI"))
    return articles


def fetch_scraped_articles() -> list[Article]:
    articles = []
    for name, base, index_url, prefix in SCRAPED_SOURCES:
        try:
            fetched = _fetch_source(name, base, index_url, prefix)
            articles.extend(fetched)
            logger.info("%s: %d articles", name, len(fetched))
        except Exception as exc:
            logger.warning("%s failed: %s", name, exc)
    return articles
