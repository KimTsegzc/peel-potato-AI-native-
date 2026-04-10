from __future__ import annotations

from typing import Iterator

from .... import LLMProvider
from ....features.conversation_context import finalize_conversation, prepare_conversation
from ....settings import get_settings
from ...contracts import AgentRequest, AgentResponse
from ..base import BaseSkill


class DirectChatSkill(BaseSkill):
    """Compatibility skill that forwards directly to the existing LLM provider."""

    name = "direct_chat"
    display_name = "通用对话"
    description = "通用对话兜底技能，处理闲聊、开放问答以及不属于专门业务技能的问题。"
    routing_hints = (
        "普通闲聊、问候、开放式问答",
        "无法明确归属到某个内部业务技能的问题",
        "外部机构、外部客服电话、泛生活类问题",
    )
    avoid_hints = (
        "明确要求查询分行内部职能分工、岗位负责人与办公号码",
    )
    routing_examples = (
        "hi",
        "客户咨询保险业务找谁",
        "今天几点了",
    )
    manual_relpath = "SKILL.md"

    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        settings = get_settings()
        prepared = prepare_conversation(
            user_input=request.user_input,
            session_id=request.session_id,
            request_started_at=request.request_started_at,
            settings=settings,
        )
        for event in LLMProvider.stream_messages(
            messages=prepared.messages,
            model=request.model,
            smooth=request.smooth,
        ):
            if event.get("type") == "done":
                metrics = dict(event.get("metrics", {}))
                metrics["context"] = {
                    **prepared.metrics(),
                    **finalize_conversation(
                        prepared=prepared,
                        user_input=request.user_input,
                        assistant_output=event.get("content", ""),
                        settings=settings,
                    ),
                }
                event = {**event, "metrics": metrics}
            yield event

    def run_once(self, request: AgentRequest) -> AgentResponse:
        settings = get_settings()
        prepared = prepare_conversation(
            user_input=request.user_input,
            session_id=request.session_id,
            request_started_at=request.request_started_at,
            settings=settings,
        )
        content, metrics = LLMProvider.with_metrics_messages(
            messages=prepared.messages,
            model=request.model,
        )
        metrics["context"] = {
            **prepared.metrics(),
            **finalize_conversation(
                prepared=prepared,
                user_input=request.user_input,
                assistant_output=content,
                settings=settings,
            ),
        }
        return AgentResponse(content=content, metrics=metrics)
