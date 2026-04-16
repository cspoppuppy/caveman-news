import asyncio
import logging

from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType
from copilot.session import PermissionHandler

logger = logging.getLogger(__name__)

_PROMPT = (
    "British English. Drop articles/filler/hedging/pleasantries. "
    "Fragments OK. Short synonyms. Technical terms exact. Punchy grunts.\n\n"
    "---\n\nCaveman mode. Summarise this AI news article. Max 120 words.\n\n"
    "Title: {title}\n\n{content}"
)


async def summarise(title: str, content: str) -> str | None:
    parts: list[str] = []
    done = asyncio.Event()
    try:
        async with CopilotClient() as client:
            async with await client.create_session(
                on_permission_request=PermissionHandler.approve_all, model="gpt-5-mini"
            ) as session:
                def on_event(event):
                    if event.type == SessionEventType.ASSISTANT_MESSAGE and event.data.content:
                        parts.append(event.data.content)
                    elif event.type == SessionEventType.SESSION_IDLE:
                        done.set()
                session.on(on_event)
                await session.send(_PROMPT.format(title=title, content=content[:2000]))
                await asyncio.wait_for(done.wait(), timeout=30)
        return "".join(parts).strip() or None
    except asyncio.TimeoutError:
        logger.warning("LLM timeout: %s", title)
    except Exception as e:
        logger.warning("LLM error '%s': %s", title, e)
    return None
