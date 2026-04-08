from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from ..contracts import AgentRequest, AgentResponse


@dataclass(frozen=True, slots=True)
class SkillDescriptor:
    name: str
    description: str
    routing_hints: tuple[str, ...] = ()
    avoid_hints: tuple[str, ...] = ()
    routing_examples: tuple[str, ...] = ()
    manual_excerpt: str = ""

    def render_for_router(self) -> str:
        parts = [f"技能名：{self.name}", f"用途：{self.description or '未说明'}"]
        if self.routing_hints:
            parts.append("适用场景：" + "；".join(self.routing_hints))
        if self.avoid_hints:
            parts.append("不要用于：" + "；".join(self.avoid_hints))
        if self.routing_examples:
            parts.append("示例问法：" + "；".join(self.routing_examples))
        if self.manual_excerpt:
            parts.append("技能说明书摘录：" + self.manual_excerpt)
        return "\n".join(parts)


class BaseSkill(ABC):
    name: str
    description: str = ""
    routing_hints: tuple[str, ...] = ()
    avoid_hints: tuple[str, ...] = ()
    routing_examples: tuple[str, ...] = ()
    manual_relpath: str | None = None

    def descriptor(self) -> SkillDescriptor:
        description = (self.description or inspect.getdoc(self.__class__) or "").strip()
        return SkillDescriptor(
            name=self.name,
            description=description,
            routing_hints=tuple(self.routing_hints),
            avoid_hints=tuple(self.avoid_hints),
            routing_examples=tuple(self.routing_examples),
            manual_excerpt=self._read_manual_excerpt(),
        )

    def _read_manual_excerpt(self, max_chars: int = 1200) -> str:
        manual_path = self._resolve_manual_path()
        if manual_path is None or not manual_path.exists():
            return ""
        text = manual_path.read_text(encoding="utf-8").strip()
        if len(text) <= max_chars:
            return text
        return text[: max(0, max_chars - 3)] + "..."

    def _resolve_manual_path(self) -> Path | None:
        if not self.manual_relpath:
            return None
        module_file = Path(inspect.getfile(self.__class__)).resolve()
        return module_file.parent / self.manual_relpath

    @abstractmethod
    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        raise NotImplementedError

    @abstractmethod
    def run_once(self, request: AgentRequest) -> AgentResponse:
        raise NotImplementedError
