import asyncio
import logging

from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType
from copilot.session import PermissionHandler

logger = logging.getLogger(__name__)

# Distilled from skills/caveman/SKILL.md — full mode, news-summary flavour
CAVEMAN_SKILL = (
    "British English. Drop articles/filler/hedging/pleasantries. "
    "Fragments OK. Short synonyms. Technical terms exact. Punchy grunts."
)
FALLBACK_SUMMARY = "[UGH. UGG NO GET SUMMARY. BRAIN HURT.]"


async def summarise(title: str, content: str) -> str:
    """Summarise a news article using the installed caveman skill."""
    prompt = (
        f"{CAVEMAN_SKILL}\n\n"
        f"---\n\n"
        f"Caveman mode. Summarise this AI news article. Max 120 words.\n\n"
        f"Title: {title}\n\n"
        f"{content[:2000]}"
    )
    result_parts: list[str] = []
    done = asyncio.Event()

    try:
        async with CopilotClient() as client:
            async with await client.create_session(
                on_permission_request=PermissionHandler.approve_all,
                model="gpt-5-mini",
            ) as session:
                def on_event(event):
                    if event.type == SessionEventType.ASSISTANT_MESSAGE:
                        if event.data.content:
                            result_parts.append(event.data.content)
                    elif event.type == SessionEventType.SESSION_IDLE:
                        done.set()

                session.on(on_event)
                await session.send(prompt)
                await asyncio.wait_for(done.wait(), timeout=30)

        return "".join(result_parts).strip() or FALLBACK_SUMMARY

    except asyncio.TimeoutError:
        logger.warning("LLM timeout for article: %s", title)
        return FALLBACK_SUMMARY
    except Exception as e:
        logger.warning("LLM error for article '%s': %s", title, e)
        return FALLBACK_SUMMARY


async def summarise_many(articles: list[tuple[str, str]]) -> list[str]:
    """Summarise multiple (title, content) pairs sequentially."""
    results = []
    for title, content in articles:
        summary = await summarise(title, content)
        results.append(summary)
    return results


if __name__ == "__main__":
    async def _test():
        print(f"Prompt ({len(CAVEMAN_SKILL)} chars): {CAVEMAN_SKILL}")
        result = await summarise(
            "OpenAI launches GPT-5",
            "OpenAI today announced the release of GPT-5, its most capable model yet..."
        )
        print(result)
    asyncio.run(_test())
