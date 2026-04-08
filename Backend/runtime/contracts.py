from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class AgentRequest:
    user_input: str
    model: str | None = None
    smooth: bool = True
    session_id: str | None = None
    request_started_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentResponse:
    content: str
    metrics: dict[str, Any] = field(default_factory=dict)
