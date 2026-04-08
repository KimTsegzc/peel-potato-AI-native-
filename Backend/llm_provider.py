from __future__ import annotations

import json
import threading
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from openai import OpenAI


def _ensure_repo_root_on_path_for_direct_run() -> None:
    if __package__ not in (None, ""):
        return
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_ensure_repo_root_on_path_for_direct_run()

if __package__ in (None, ""):
    from Backend.settings import AVAILABLE_MODELS, Settings, get_settings, load_system_prompt
else:
    from .settings import AVAILABLE_MODELS, Settings, get_settings, load_system_prompt


def get_model_list() -> list[str]:
    """Return the registry of available models (for frontend dropdowns etc.)."""
    return AVAILABLE_MODELS

VERBOSE_MODE_DEFAULT = True
STREAM_MODE_DEFAULT = True
STREAM_SMOOTH_MIN_CHARS = 12
STREAM_SMOOTH_MAX_WAIT_SECONDS = 0.05


def build_client(settings: Settings) -> OpenAI:
    if not settings.api_key:
        raise RuntimeError(
            "Missing API key. Set DASHSCOPE_API_KEY or ALIYUN_BAILIAN_API_KEY in the environment or .env."
        )

    return OpenAI(api_key=settings.api_key, base_url=settings.base_url)


def _resolve_model(settings: Settings, model: Optional[str] = None) -> str:
    return model or settings.model


def _resolve_request_options(settings: Settings) -> dict:
    """Pick optional generation parameters from settings when provided."""
    options = {}
    for key in ("temperature", "top_p", "max_tokens"):
        value = getattr(settings, key)
        if value is not None:
            options[key] = value
    return options


def _resolve_enable_search(settings: Settings, enable_search: Optional[bool] = None) -> bool:
    if enable_search is None:
        return bool(settings.llm_enable_search)
    return bool(enable_search)


def _build_extra_body(enable_search: bool) -> dict:
    return {"enable_search": enable_search}


def _safe_json_loads(raw_text: str) -> Any:
    if not raw_text:
        return {}
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text


def _extract_usage_metrics(completion) -> dict:
    usage = getattr(completion, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def _extract_message_content(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(getattr(item, "text", "") or ""))
        return "".join(parts)
    return str(content or "")


def _extract_tool_calls(message) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for tool_call in getattr(message, "tool_calls", None) or []:
        function = getattr(tool_call, "function", None)
        arguments_text = str(getattr(function, "arguments", "") or "")
        calls.append(
            {
                "id": getattr(tool_call, "id", None),
                "type": getattr(tool_call, "type", None) or "function",
                "function": {
                    "name": getattr(function, "name", None),
                    "arguments": _safe_json_loads(arguments_text),
                    "arguments_text": arguments_text,
                },
            }
        )
    return calls


def _build_messages(settings: Settings, user_input: str) -> list[dict]:
    now = datetime.now()
    date_ctx = f"当前系统时间：{now.strftime('%Y年%m月%d日 %H:%M')}\n\n"
    return [
        {"role": "system", "content": date_ctx + load_system_prompt()},
        {"role": "user", "content": user_input},
    ]


def _create_chat_completion(
    *,
    settings: Settings,
    messages: list[dict],
    model: Optional[str],
    enable_search: Optional[bool],
    stream: bool,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | str | None = None,
):
    client = build_client(settings)
    model_name = _resolve_model(settings, model=model)
    request_options = _resolve_request_options(settings)
    resolved_enable_search = _resolve_enable_search(settings, enable_search=enable_search)
    create_kwargs: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": stream,
        "extra_body": _build_extra_body(resolved_enable_search),
        **request_options,
    }
    if stream:
        create_kwargs["stream_options"] = {"include_usage": True}
    if tools:
        create_kwargs["tools"] = tools
    if tool_choice is not None:
        create_kwargs["tool_choice"] = tool_choice
    return client.chat.completions.create(**create_kwargs), model_name, request_options, resolved_enable_search


def _stream_chat_completion(
    *,
    settings: Settings,
    messages: list[dict],
    model: Optional[str],
    smooth: bool,
    enable_search: Optional[bool],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | str | None = None,
) -> Iterator[dict]:
    started = time.perf_counter()
    yield {"type": "pulse", "stage": "accepted", "elapsed_seconds": 0.0}

    stream, model_name, request_options, resolved_enable_search = _create_chat_completion(
        settings=settings,
        messages=messages,
        model=model,
        enable_search=enable_search,
        stream=True,
        tools=tools,
        tool_choice=tool_choice,
    )

    all_parts = []
    pending_parts = []
    last_emit = started
    first_token_emitted = False
    first_token_latency_seconds = None
    usage_metrics = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }
    tool_call_parts: dict[int, dict[str, Any]] = {}

    for chunk in stream:
        chunk_usage = _extract_usage_metrics(chunk)
        if chunk_usage["total_tokens"] is not None:
            usage_metrics = chunk_usage

        if not getattr(chunk, "choices", None):
            continue

        delta = chunk.choices[0].delta
        for tool_delta in getattr(delta, "tool_calls", None) or []:
            call_index = int(getattr(tool_delta, "index", 0) or 0)
            current = tool_call_parts.setdefault(
                call_index,
                {"id": None, "type": "function", "function": {"name": "", "arguments_text": ""}},
            )
            if getattr(tool_delta, "id", None):
                current["id"] = tool_delta.id
            if getattr(tool_delta, "type", None):
                current["type"] = tool_delta.type
            function = getattr(tool_delta, "function", None)
            if function is not None:
                if getattr(function, "name", None):
                    current["function"]["name"] = function.name
                if getattr(function, "arguments", None):
                    current["function"]["arguments_text"] += function.arguments

        piece = getattr(delta, "content", None)
        if piece:
            if not first_token_emitted:
                first_token_emitted = True
                first_token_latency_seconds = time.perf_counter() - started
                yield {
                    "type": "pulse",
                    "stage": "first_token",
                    "elapsed_seconds": first_token_latency_seconds,
                }

            all_parts.append(piece)
            if not smooth:
                yield {"type": "delta", "content": piece}
                continue

            pending_parts.append(piece)
            pending_text = "".join(pending_parts)
            now = time.perf_counter()
            should_flush = (
                len(pending_text) >= STREAM_SMOOTH_MIN_CHARS
                or (now - last_emit) >= STREAM_SMOOTH_MAX_WAIT_SECONDS
            )
            if should_flush:
                yield {"type": "delta", "content": pending_text}
                pending_parts.clear()
                last_emit = now

    if pending_parts:
        yield {"type": "delta", "content": "".join(pending_parts)}

    elapsed = time.perf_counter() - started
    content = "".join(all_parts)
    tool_calls = []
    for index in sorted(tool_call_parts):
        item = tool_call_parts[index]
        arguments_text = item["function"].get("arguments_text", "")
        tool_calls.append(
            {
                "id": item.get("id"),
                "type": item.get("type") or "function",
                "function": {
                    "name": item["function"].get("name") or None,
                    "arguments": _safe_json_loads(arguments_text),
                    "arguments_text": arguments_text,
                },
            }
        )
    throughput_tokens = usage_metrics["completion_tokens"] or usage_metrics["total_tokens"]
    metrics = {
        "model": model_name,
        "base_url": settings.base_url,
        "enable_search": resolved_enable_search,
        "request_options": request_options,
        "tool_choice_used": tool_choice,
        "tool_count": len(tools or []),
        "first_token_latency_seconds": first_token_latency_seconds,
        "latency_seconds": elapsed,
        "throughput_tokens_per_second": (
            (throughput_tokens / elapsed) if throughput_tokens and elapsed > 0 else None
        ),
        **usage_metrics,
    }
    yield {"type": "done", "content": content, "metrics": metrics, "tool_calls": tool_calls}


def LLM_stream_messages(
    messages: list[dict],
    model: Optional[str] = None,
    smooth: bool = True,
    enable_search: Optional[bool] = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | str | None = None,
) -> Iterator[dict]:
    settings = get_settings()
    yield from _stream_chat_completion(
        settings=settings,
        messages=messages,
        model=model,
        smooth=smooth,
        enable_search=enable_search,
        tools=tools,
        tool_choice=tool_choice,
    )


def LLM_with_metrics_messages(
    messages: list[dict],
    model: Optional[str] = None,
    enable_search: Optional[bool] = None,
) -> tuple[str, dict]:
    final_content = ""
    final_metrics = {}
    for event in LLM_stream_messages(messages, model=model, smooth=True, enable_search=enable_search):
        if event.get("type") == "done":
            final_content = event.get("content", "")
            final_metrics = event.get("metrics", {})
    return final_content, final_metrics


def LLM_with_response_messages(
    messages: list[dict],
    model: Optional[str] = None,
    enable_search: Optional[bool] = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    started = time.perf_counter()
    completion, model_name, request_options, resolved_enable_search = _create_chat_completion(
        settings=settings,
        messages=messages,
        model=model,
        enable_search=enable_search,
        stream=False,
        tools=tools,
        tool_choice=tool_choice,
    )
    elapsed = time.perf_counter() - started
    message = completion.choices[0].message if getattr(completion, "choices", None) else None
    usage_metrics = _extract_usage_metrics(completion)
    tool_calls = _extract_tool_calls(message) if message is not None else []
    return {
        "content": _extract_message_content(message) if message is not None else "",
        "tool_calls": tool_calls,
        "metrics": {
            "model": model_name,
            "base_url": settings.base_url,
            "enable_search": resolved_enable_search,
            "request_options": request_options,
            "tool_choice_used": tool_choice,
            "tool_count": len(tools or []),
            "latency_seconds": elapsed,
            **usage_metrics,
        },
    }


def LLM_stream(
    user_input: str,
    model: Optional[str] = None,
    smooth: bool = True,
    enable_search: Optional[bool] = None,
) -> Iterator[dict]:
    """Stream model output as events for backend usage.

    Yields events with shape:
    - {"type": "pulse", "stage": "accepted|first_token", "elapsed_seconds": float}
    - {"type": "delta", "content": "..."}
    - {"type": "done", "content": "full text", "metrics": {...}}
    """
    settings = get_settings()
    yield from _stream_chat_completion(
        settings=settings,
        messages=_build_messages(settings, user_input),
        model=model,
        smooth=smooth,
        enable_search=enable_search,
    )


def LLM_with_metrics(
    user_input: str,
    model: Optional[str] = None,
    enable_search: Optional[bool] = None,
) -> tuple[str, dict]:
    """Call LLM and return assistant content plus runtime metrics."""
    final_content = ""
    final_metrics = {}
    for event in LLM_stream(user_input, model=model, enable_search=enable_search):
        if event.get("type") == "done":
            final_content = event.get("content", "")
            final_metrics = event.get("metrics", {})
    return final_content, final_metrics


def LLM(
    user_input: str,
    model: Optional[str] = None,
    enable_search: Optional[bool] = None,
) -> str:
    """Call LLM and return assistant content only."""
    content, _ = LLM_with_metrics(user_input, model=model, enable_search=enable_search)
    return content


def _format_verbose_metrics(metrics: dict) -> str:
    throughput = metrics.get("throughput_tokens_per_second")
    throughput_text = f"{throughput:.2f} tokens/s" if throughput is not None else "N/A"
    first_token_latency = metrics.get("first_token_latency_seconds")
    first_token_latency_text = (
        f"{first_token_latency:.3f}s" if first_token_latency is not None else "N/A"
    )
    return (
        f"[VERBOSE] model={metrics.get('model')}\n"
        f"[VERBOSE] enable_search={metrics.get('enable_search')}\n"
        f"[VERBOSE] first_token_latency={first_token_latency_text}\n"
        f"[VERBOSE] latency={metrics.get('latency_seconds', 0.0):.3f}s\n"
        f"[VERBOSE] usage prompt={metrics.get('prompt_tokens')} completion={metrics.get('completion_tokens')} total={metrics.get('total_tokens')}\n"
        f"[VERBOSE] throughput={throughput_text}"
    )


def _start_cli_wait_spinner(prefix: str = "output >> "):
    stop_event = threading.Event()

    def _spin() -> None:
        frames = "|/-\\"
        index = 0
        while not stop_event.is_set():
            frame = frames[index % len(frames)]
            print(f"\r{prefix}[waiting {frame}]", end="", flush=True)
            index += 1
            stop_event.wait(0.12)
        print(f"\r{prefix}", end="", flush=True)

    thread = threading.Thread(target=_spin, daemon=True)
    thread.start()
    return stop_event, thread


def _stop_cli_wait_spinner(stop_event, thread) -> None:
    if stop_event is None or thread is None:
        return
    stop_event.set()
    thread.join(timeout=0.4)


class LLMProvider:
    """Facade class for external imports from Backend."""

    @staticmethod
    def stream(
        user_input: str,
        model: Optional[str] = None,
        smooth: bool = True,
        enable_search: Optional[bool] = None,
    ) -> Iterator[dict]:
        yield from LLM_stream(
            user_input=user_input,
            model=model,
            smooth=smooth,
            enable_search=enable_search,
        )

    @staticmethod
    def stream_messages(
        messages: list[dict],
        model: Optional[str] = None,
        smooth: bool = True,
        enable_search: Optional[bool] = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | str | None = None,
    ) -> Iterator[dict]:
        yield from LLM_stream_messages(
            messages=messages,
            model=model,
            smooth=smooth,
            enable_search=enable_search,
            tools=tools,
            tool_choice=tool_choice,
        )

    @staticmethod
    def with_metrics(
        user_input: str,
        model: Optional[str] = None,
        enable_search: Optional[bool] = None,
    ) -> tuple[str, dict]:
        return LLM_with_metrics(
            user_input=user_input,
            model=model,
            enable_search=enable_search,
        )

    @staticmethod
    def with_metrics_messages(
        messages: list[dict],
        model: Optional[str] = None,
        enable_search: Optional[bool] = None,
    ) -> tuple[str, dict]:
        return LLM_with_metrics_messages(
            messages=messages,
            model=model,
            enable_search=enable_search,
        )

    @staticmethod
    def with_response_messages(
        messages: list[dict],
        model: Optional[str] = None,
        enable_search: Optional[bool] = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        return LLM_with_response_messages(
            messages=messages,
            model=model,
            enable_search=enable_search,
            tools=tools,
            tool_choice=tool_choice,
        )

    @staticmethod
    def text(
        user_input: str,
        model: Optional[str] = None,
        enable_search: Optional[bool] = None,
    ) -> str:
        return LLM(user_input=user_input, model=model, enable_search=enable_search)


def main() -> None:
    verbose_mode = VERBOSE_MODE_DEFAULT
    stream_mode = STREAM_MODE_DEFAULT
    print("LLM Provider ready. Type your prompt after 'input >>'. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("input >> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nbye")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("bye")
            break
        if not user_input:
            continue

        try:
            if stream_mode:
                print("output >> ", end="", flush=True)
                final_metrics = {}
                spinner_stop_event = None
                spinner_thread = None
                for event in LLM_stream(user_input):
                    if event.get("type") == "pulse":
                        if event.get("stage") == "accepted" and spinner_stop_event is None:
                            spinner_stop_event, spinner_thread = _start_cli_wait_spinner("output >> ")
                        elif event.get("stage") == "first_token":
                            _stop_cli_wait_spinner(spinner_stop_event, spinner_thread)
                            spinner_stop_event, spinner_thread = None, None
                    elif event.get("type") == "delta":
                        _stop_cli_wait_spinner(spinner_stop_event, spinner_thread)
                        spinner_stop_event, spinner_thread = None, None
                        print(event.get("content", ""), end="", flush=True)
                    elif event.get("type") == "done":
                        final_metrics = event.get("metrics", {})
                _stop_cli_wait_spinner(spinner_stop_event, spinner_thread)
                print()
                if verbose_mode:
                    print(_format_verbose_metrics(final_metrics))
            else:
                answer, metrics = LLM_with_metrics(user_input)
                print(f"output >> {answer}")
                if verbose_mode:
                    print(_format_verbose_metrics(metrics))
        except KeyboardInterrupt:
            print("\noutput >> [CANCELLED]")
        except Exception as exc:
            print(f"output >> [ERROR] {exc}")


if __name__ == "__main__":
    main()