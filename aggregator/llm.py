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


async def summarise(title: str, content: str) -> str | None:
    """Summarise a news article. Returns None on failure — caller should skip."""
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

        summary = "".join(result_parts).strip()
        return summary if summary else None

    except asyncio.TimeoutError:
        logger.warning("LLM timeout for article: %s", title)
        return None
    except Exception as e:
        logger.warning("LLM error for article '%s': %s", title, e)
        return None
