from __future__ import annotations

from typing import Iterator

from .contracts import AgentRequest, AgentResponse
from .registry import SkillRegistry, ToolRegistry
from .router import RouteDecision, SkillRouter
from .skills import CCBGetHandlerSkill, DirectChatSkill, SendEmailSkill


class AgentRuntime:
    """Stable scheduling shell for skill-tool architecture evolution."""

    def __init__(self) -> None:
        self.skills = SkillRegistry()
        self.tools = ToolRegistry()
        self.router = SkillRouter()
        self._bootstrap_defaults()

    def _bootstrap_defaults(self) -> None:
        self.skills.register(CCBGetHandlerSkill())
        self.skills.register(SendEmailSkill())
        self.skills.register(DirectChatSkill())

    def _select_route(self, request: AgentRequest) -> RouteDecision:
        return self.router.select_skill(request, self.skills)

    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        decision = self._select_route(request)
        skill = self.skills.get(decision.skill_name)
        yield {
            "type": "skill",
            "stage": "selected",
            "skill": {
                "name": decision.skill_name,
                "label": decision.skill_display_name,
            },
            "routing": {
                "source": decision.source,
                "reason": decision.reason,
                "fallback_used": decision.fallback_used,
            },
        }
        for event in skill.run_stream(request):
            if event.get("type") == "done":
                metrics = dict(event.get("metrics", {}))
                metrics["routing"] = decision.metrics()
                event = {**event, "metrics": metrics}
            yield event

    def run_once(self, request: AgentRequest) -> AgentResponse:
        decision = self._select_route(request)
        skill = self.skills.get(decision.skill_name)
        response = skill.run_once(request)
        response.metrics["routing"] = decision.metrics()
        return response


_RUNTIME: AgentRuntime | None = None


def get_runtime() -> AgentRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = AgentRuntime()
    return _RUNTIME
