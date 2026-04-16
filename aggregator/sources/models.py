from dataclasses import dataclass, field
from datetime import date


@dataclass
class Article:
    title: str
    url: str
    content: str
    source: str
    category: str = "AI"
    published_date: date | None = field(default=None, compare=False)
