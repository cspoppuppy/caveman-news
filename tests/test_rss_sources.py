"""Tests for rss_sources.py — TDD Red-Green cycle."""
import types
from unittest.mock import MagicMock, patch

import pytest

from rss_sources import Article, RSS_FEEDS, _strip_html, fetch_rss_articles


# ---------------------------------------------------------------------------
# Article dataclass
# ---------------------------------------------------------------------------

class TestArticleDataclass:
    def test_has_all_four_fields(self):
        a = Article(title="t", url="u", content="c", source="s")
        assert a.title == "t"
        assert a.url == "u"
        assert a.content == "c"
        assert a.source == "s"

    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(Article)


# ---------------------------------------------------------------------------
# RSS_FEEDS definition
# ---------------------------------------------------------------------------

class TestRSSFeeds:
    def test_has_six_feeds(self):
        assert len(RSS_FEEDS) == 6

    def test_all_feeds_are_tuples_of_two_strings(self):
        for item in RSS_FEEDS:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert all(isinstance(v, str) for v in item)

    def test_expected_sources_present(self):
        names = [name for name, _ in RSS_FEEDS]
        assert "OpenAI" in names
        assert "GitHub Copilot" in names
        assert "Google AI" in names
        assert "HuggingFace" in names
        assert "The Verge AI" in names
        assert "VentureBeat AI" in names


# ---------------------------------------------------------------------------
# _strip_html helper
# ---------------------------------------------------------------------------

class TestStripHtml:
    def test_removes_simple_tags(self):
        assert _strip_html("<p>Hello</p>") == "Hello"

    def test_removes_nested_tags(self):
        assert _strip_html("<div><span>text</span></div>") == "text"

    def test_passthrough_plain_text(self):
        assert _strip_html("no tags here") == "no tags here"

    def test_empty_string(self):
        assert _strip_html("") == ""


# ---------------------------------------------------------------------------
# fetch_rss_articles
# ---------------------------------------------------------------------------

def _make_entry(title="Test Title", link="https://example.com/1", summary="<p>Body</p>"):
    entry = MagicMock()
    entry.get = lambda key, default="": {
        "title": title,
        "link": link,
        "summary": summary,
    }.get(key, default)
    return entry


def _make_feed(entries):
    feed = MagicMock()
    feed.entries = entries
    return feed


class TestFetchRSSArticles:
    def test_returns_list(self):
        with patch("rss_sources.feedparser.parse", return_value=_make_feed([])):
            result = fetch_rss_articles()
        assert isinstance(result, list)

    def test_parses_valid_entry(self):
        entry = _make_entry(title="AI News", link="https://example.com/ai", summary="<b>Bold</b> text")
        feed = _make_feed([entry])

        with patch("rss_sources.feedparser.parse", return_value=feed):
            articles = fetch_rss_articles()

        assert len(articles) == len(RSS_FEEDS)  # one per source
        article = articles[0]
        assert isinstance(article, Article)
        assert article.title == "AI News"
        assert article.url == "https://example.com/ai"
        assert article.content == "Bold text"  # HTML stripped

    def test_source_name_set_correctly(self):
        entry = _make_entry()
        feed = _make_feed([entry])

        with patch("rss_sources.feedparser.parse", return_value=feed):
            articles = fetch_rss_articles()

        source_names = {a.source for a in articles}
        expected = {name for name, _ in RSS_FEEDS}
        assert source_names == expected

    def test_max_five_entries_per_feed(self):
        entries = [_make_entry(link=f"https://example.com/{i}") for i in range(10)]
        feed = _make_feed(entries)

        with patch("rss_sources.feedparser.parse", return_value=feed):
            articles = fetch_rss_articles()

        per_source = {}
        for a in articles:
            per_source.setdefault(a.source, 0)
            per_source[a.source] += 1

        for count in per_source.values():
            assert count <= 5

    def test_skips_entry_with_empty_title(self):
        bad = _make_entry(title="", link="https://example.com/no-title")
        good = _make_entry(title="Good", link="https://example.com/good")
        feed = _make_feed([bad, good])

        with patch("rss_sources.feedparser.parse", return_value=feed):
            articles = fetch_rss_articles()

        titles = [a.title for a in articles]
        assert "" not in titles
        assert "Good" in titles

    def test_skips_entry_with_empty_url(self):
        bad = _make_entry(title="No URL", link="")
        good = _make_entry(title="Has URL", link="https://example.com/has-url")
        feed = _make_feed([bad, good])

        with patch("rss_sources.feedparser.parse", return_value=feed):
            articles = fetch_rss_articles()

        urls = [a.url for a in articles]
        assert "" not in urls

    def test_content_truncated_to_3000_chars(self):
        long_text = "A" * 5000
        entry = _make_entry(summary=long_text)
        feed = _make_feed([entry])

        with patch("rss_sources.feedparser.parse", return_value=feed):
            articles = fetch_rss_articles()

        for a in articles:
            assert len(a.content) <= 3000

    def test_feed_failure_does_not_crash(self):
        call_count = 0

        def parse_side_effect(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("network error")
            return _make_feed([_make_entry()])

        with patch("rss_sources.feedparser.parse", side_effect=parse_side_effect):
            articles = fetch_rss_articles()  # must not raise

        # remaining feeds still processed
        assert len(articles) == len(RSS_FEEDS) - 1

    def test_feed_failure_logs_warning(self, caplog):
        import logging

        def parse_side_effect(url):
            raise RuntimeError("boom")

        with patch("rss_sources.feedparser.parse", side_effect=parse_side_effect):
            with caplog.at_level(logging.WARNING, logger="rss_sources"):
                fetch_rss_articles()

        assert any("boom" in r.message or "boom" in str(r.exc_info) for r in caplog.records)

    def test_falls_back_to_description_when_no_summary(self):
        entry = MagicMock()
        entry.get = lambda key, default="": {
            "title": "Fallback",
            "link": "https://example.com/fb",
            "summary": "",
            "description": "desc text",
        }.get(key, default)
        feed = _make_feed([entry])

        with patch("rss_sources.feedparser.parse", return_value=feed):
            articles = fetch_rss_articles()

        assert any(a.content == "desc text" for a in articles)
