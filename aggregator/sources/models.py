from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    title: str
    url: str
    content: str
    source: str
    category: str = "AI"
    published_at: datetime | None = field(default=None, compare=False)
