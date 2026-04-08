from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import LLMProvider
from ..settings import get_settings
from .contracts import AgentRequest
from .registry import SkillRegistry
from .skills.base import SkillDescriptor


_ROUTER_PROMPT = (
    "你是智能体技能路由器。你的唯一任务是在已注册技能中选择一个最合适的技能。\n"
    "必须使用 tool calling 调用 select_skill，不能直接输出自然语言答案。\n"
    "如果问题是普通闲聊、开放问答、外部机构客服电话、外部保险公司、外部律师、监管热线、通用建议，优先选择 direct_chat。\n"
    "只有当用户明确在问行内内部职能分工、哪个部门/岗位/负责人承接、内部接口人、办公号码时，才选择 skill_ccb_get_handler。\n"
    "如果不确定，选择 direct_chat，不要冒进。\n\n"
    "以下是当前可用技能说明：\n"
)


def _normalize_user_input(user_input: str) -> str:
    return (user_input or "").replace("user:", "", 1).strip()


def _build_router_tool(descriptors: tuple[SkillDescriptor, ...]) -> list[dict[str, Any]]:
    skill_names = [descriptor.name for descriptor in descriptors]
    return [
        {
            "type": "function",
            "function": {
                "name": "select_skill",
                "description": "Select exactly one registered skill to handle the current user request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "enum": skill_names,
                            "description": "The registered skill name that should handle this request.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Short reason for the routing decision.",
                        },
                    },
                    "required": ["skill_name", "reason"],
                    "additionalProperties": False,
                },
            },
        }
    ]


def _build_router_messages(
    *,
    user_input: str,
    descriptors: tuple[SkillDescriptor, ...],
) -> list[dict[str, str]]:
    rendered_skills = "\n\n".join(descriptor.render_for_router() for descriptor in descriptors)
    return [
        {
            "role": "system",
            "content": _ROUTER_PROMPT + rendered_skills,
        },
        {
            "role": "user",
            "content": f"用户问题：{_normalize_user_input(user_input)}",
        },
    ]


def _default_skill_name(skills: SkillRegistry) -> str:
    names = tuple(skills.names())
    if "direct_chat" in names:
        return "direct_chat"
    if not names:
        raise ValueError("No skills registered in runtime")
    return names[0]


@dataclass(frozen=True, slots=True)
class RouteDecision:
    skill_name: str
    source: str
    reason: str
    model: str | None = None
    fallback_used: bool = False
    llm_metrics: dict[str, Any] = field(default_factory=dict)

    def metrics(self) -> dict[str, Any]:
        return {
            "selected_skill": self.skill_name,
            "source": self.source,
            "reason": self.reason,
            "model": self.model,
            "fallback_used": self.fallback_used,
            "llm": self.llm_metrics,
        }


class SkillRouter:
    def select_skill(self, request: AgentRequest, skills: SkillRegistry) -> RouteDecision:
        settings = get_settings()
        default_skill = _default_skill_name(skills)
        descriptors = skills.descriptors()
        if len(descriptors) <= 1:
            return RouteDecision(
                skill_name=default_skill,
                source="static",
                reason="only_registered_skill",
            )

        if not settings.skill_routing_enabled or not settings.api_key:
            return self._fallback_decision(
                default_skill=default_skill,
                reason="router_disabled_or_missing_api_key",
            )

        try:
            response = LLMProvider.with_response_messages(
                messages=_build_router_messages(user_input=request.user_input, descriptors=descriptors),
                model=settings.skill_router_model,
                enable_search=False,
                tools=_build_router_tool(descriptors),
                tool_choice={"type": "function", "function": {"name": "select_skill"}},
            )
        except Exception as exc:
            return self._fallback_decision(
                default_skill=default_skill,
                reason=f"router_exception:{exc}",
            )

        selected_skill, reason = self._extract_tool_selection(response.get("tool_calls", []))
        if not selected_skill or selected_skill not in set(skills.names()):
            return self._fallback_decision(
                default_skill=default_skill,
                reason="router_invalid_selection",
                llm_metrics=response.get("metrics", {}),
            )

        return RouteDecision(
            skill_name=selected_skill,
            source="llm_tool_call",
            reason=reason or "router_selected_skill",
            model=settings.skill_router_model,
            fallback_used=False,
            llm_metrics=response.get("metrics", {}),
        )

    @staticmethod
    def _extract_tool_selection(tool_calls: list[dict[str, Any]]) -> tuple[str | None, str | None]:
        for tool_call in tool_calls or []:
            function = tool_call.get("function", {})
            if function.get("name") != "select_skill":
                continue
            arguments = function.get("arguments")
            if not isinstance(arguments, dict):
                continue
            skill_name = str(arguments.get("skill_name", "") or "").strip()
            reason = str(arguments.get("reason", "") or "").strip()
            return skill_name or None, reason or None
        return None, None

    def _fallback_decision(
        self,
        *,
        default_skill: str,
        reason: str,
        llm_metrics: dict[str, Any] | None = None,
    ) -> RouteDecision:
        return RouteDecision(
            skill_name=default_skill,
            source="fallback_default",
            reason=reason,
            model=None,
            fallback_used=True,
            llm_metrics=llm_metrics or {},
        )