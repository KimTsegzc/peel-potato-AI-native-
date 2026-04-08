from __future__ import annotations

from typing import Iterator

from ... import LLMProvider
from ...conversation_context import finalize_conversation, prepare_conversation
from ...settings import get_settings
from ..contracts import AgentRequest, AgentResponse
from .base import BaseSkill


class DirectChatSkill(BaseSkill):
    """Compatibility skill that forwards directly to the existing LLM provider."""

    name = "direct_chat"

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
