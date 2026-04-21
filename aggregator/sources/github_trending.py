"""GitHub Trending source — scrapes daily trending repos and filters for AI/ML relevance."""
import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from .models import Article

logger = logging.getLogger(__name__)

_URL = "https://github.com/trending?since=daily"
_HEADERS = {"User-Agent": "CavemanNewsBot/1.0 (github.com/cspoppuppy/caveman-news)"}
_MAX_REPOS = 10
_MAX_CHARS = 1500

_AI_KEYWORDS = {
    "ai", "ml", "llm", "gpt", "claude", "gemini", "llama", "mistral", "neural",
    "model", "inference", "embedding", "vector", "transformer", "diffusion",
    "agent", "rag", "lora", "finetune", "fine-tune", "deepseek", "qwen",
    "stable-diffusion", "openai", "anthropic", "huggingface", "langchain",
    "machine-learning", "deep-learning", "nlp", "computer-vision",
}


def _is_ai_related(name: str, description: str) -> bool:
    text = (name + " " + description).lower()
    return any(kw in text for kw in _AI_KEYWORDS)


def fetch_github_trending(since: datetime | None = None) -> list[Article]:
    try:
        resp = httpx.get(_URL, headers=_HEADERS, timeout=15, follow_redirects=True, verify=False)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("GitHub Trending failed: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    articles = []

    for repo_article in soup.select("article.Box-row"):
        a_tag = repo_article.select_one("h2 a")
        if not a_tag:
            continue
        href = a_tag.get("href", "").strip().lstrip("/")
        if not href or "/" not in href:
            continue
        url = f"https://github.com/{href}"
        name = href.replace("/", " / ")

        desc_tag = repo_article.select_one("p")
        description = desc_tag.get_text(" ", strip=True) if desc_tag else ""

        if not _is_ai_related(href, description):
            continue

        stars_tag = repo_article.select_one("a[href$='/stargazers']")
        stars = stars_tag.get_text(strip=True) if stars_tag else ""

        stars_today_tag = repo_article.select_one("span.d-inline-block.float-sm-right")
        stars_today = stars_today_tag.get_text(strip=True) if stars_today_tag else ""

        lang_tag = repo_article.select_one("span[itemprop='programmingLanguage']")
        language = lang_tag.get_text(strip=True) if lang_tag else ""

        content_parts = [description]
        if language:
            content_parts.append(f"Language: {language}")
        if stars:
            content_parts.append(f"Stars: {stars}")
        if stars_today:
            content_parts.append(f"Stars today: {stars_today}")
        content = "\n".join(content_parts)[:_MAX_CHARS]

        articles.append(Article(
            title=name,
            url=url,
            content=content,
            source="GitHub Trending",
            category="AI",
            published_at=datetime.now(timezone.utc),
        ))

        if len(articles) >= _MAX_REPOS:
            break

    logger.info("GitHub Trending: %d AI repos", len(articles))
    return articles
