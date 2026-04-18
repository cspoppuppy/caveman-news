import asyncio
import json
import logging
from typing import TYPE_CHECKING

from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType
from copilot.session import PermissionHandler

if TYPE_CHECKING:
    from aggregator.sources.models import Article

logger = logging.getLogger(__name__)

_SUMMARISE_PROMPT = (
    "British English. Drop articles/filler/hedging/pleasantries. "
    "Fragments OK. Short synonyms. Technical terms exact. Punchy grunts.\n\n"
    "---\n\nCaveman mode. Summarise this AI news article. Max 120 words.\n\n"
    "Title: {title}\n\n{content}"
)

_REVIEW_PROMPT = """\
You are reviewing a batch of AI news article titles fetched today.

Identify and remove:
1. DUPLICATES — multiple articles covering the same announcement or story. Keep only the most informative title per story.
2. OLD NEWS — articles clearly about events from weeks/months ago (historical summaries, retrospectives, evergreen explainers with no new information).

Return ONLY valid JSON, no prose:
{{"keep": [<indices of articles to keep>], "skip": [{{"index": <n>, "reason": "<duplicate of N | old news>"}}]}}

Articles:
{articles}"""


async def _llm_call(prompt: str, timeout: float = 30) -> str | None:
    """Single LLM round-trip. Returns text or None on failure."""
    parts: list[str] = []
    done = asyncio.Event()
    try:
        async with CopilotClient() as client:
            async with await client.create_session(
                on_permission_request=PermissionHandler.approve_all, model="gpt-5-mini"
            ) as session:
                def on_event(event):
                    if event.type == SessionEventType.ASSISTANT_MESSAGE and event.data and event.data.content:
                        parts.append(event.data.content)
                    elif event.type == SessionEventType.ASSISTANT_TURN_END:
                        done.set()
                session.on(on_event)
                await session.send(prompt)
                await asyncio.wait_for(done.wait(), timeout=timeout)
        return "".join(parts).strip() or None
    except asyncio.TimeoutError:
        logger.warning("LLM timeout")
    except Exception as e:
        logger.warning("LLM error: %s", e)
    return None


async def review(articles: "list[Article]") -> set[str]:
    """Return URLs of articles that pass review (not duplicate, not old news)."""
    if not articles:
        return set()
    numbered = "\n".join(f"{i}: {a.title}" for i, a in enumerate(articles))
    raw = await _llm_call(_REVIEW_PROMPT.format(articles=numbered), timeout=60)
    if not raw:
        logger.warning("Review LLM failed — keeping all %d articles", len(articles))
        return {a.url for a in articles}
    try:
        # Strip markdown code fences if present
        text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        keep_indices = set(data.get("keep", range(len(articles))))
        skipped = data.get("skip", [])
        for s in skipped:
            logger.info("Review removed [%d] %s — %s", s["index"], articles[s["index"]].title, s["reason"])
        return {articles[i].url for i in keep_indices if 0 <= i < len(articles)}
    except Exception as e:
        logger.warning("Review parse error (%s) — keeping all articles", e)
        return {a.url for a in articles}


async def summarise(title: str, content: str) -> str | None:
    result = await _llm_call(_SUMMARISE_PROMPT.format(title=title, content=content[:2000]))
    if result is None:
        logger.warning("LLM timeout: %s", title)
    return result
