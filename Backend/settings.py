from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[1]

# 支持的模型列表 —— 维护在代码里，前端从 get_model_list() 读取；
# 用户只需在 .env 中用 LLM_MODEL 指定当前选用的一个即可。
AVAILABLE_MODELS: list[str] = [
    "qwen3.5-plus",
    "qwen3-max",
    "qwen3.5-flash",
    "qwen-turbo",
    "glm-5"
]

_SOUL_FILE = REPO_ROOT / "Prompt" / "soul.md"
_DEFAULT_SOUL = ""
_SUMMARY_FILE = REPO_ROOT / "Prompt" / "llm_summary.md"
_DEFAULT_SUMMARY_PROMPT = """
# 角色
你负责把多轮聊天压缩成可供后续对话使用的滚动摘要。

# 目标
- 保留对后续回答有帮助的信息。
- 明确区分已确认事实、用户偏好、待办事项、时间敏感信息。
- 不要编造未出现的事实。

# 输出要求
- 输出纯文本 Markdown。
- 控制在 6 个小节以内。
- 如果没有信息，写“暂无”。
""".strip()


def load_system_prompt() -> str:
    """每次调用时重新读取 Prompt/soul.md，改完文件即时生效，无需重启。"""
    if _SOUL_FILE.exists():
        return _SOUL_FILE.read_text(encoding="utf-8").strip()
    # Backward compatibility for old repo layout.
    return _DEFAULT_SOUL


def load_summary_prompt() -> str:
    """每次调用时重新读取 Prompt/llm_summary.md，便于直接调试摘要提示词。"""
    if _SUMMARY_FILE.exists():
        return _SUMMARY_FILE.read_text(encoding="utf-8").strip()
    return _DEFAULT_SUMMARY_PROMPT


class Settings(BaseSettings):
    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DASHSCOPE_API_KEY",
            "ALIYUN_BAILIAN_API_KEY",
            "OPENAI_API_KEY",
            "API_KEY",
        ),
    )
    base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias=AliasChoices(
            "DASHSCOPE_BASE_URL",
            "ALIYUN_BAILIAN_BASE_URL",
            "OPENAI_BASE_URL",
            "BASE_URL",
        ),
    )
    model: str = Field(
        default=AVAILABLE_MODELS[-1],   # 默认末尾项；.env 里 LLM_MODEL 可覆盖
        validation_alias=AliasChoices("LLM_MODEL", "OPENAI_MODEL"),
    )
    temperature: float | None = Field(
        default=0.7,
        validation_alias=AliasChoices("LLM_TEMPERATURE", "TEMPERATURE"),
    )
    top_p: float | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_TOP_P", "TOP_P"),
    )
    max_tokens: int | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_MAX_TOKENS", "MAX_TOKENS"),
    )
    llm_enable_search: bool = Field(
        default=True,
        validation_alias=AliasChoices("LLM_ENABLE_SEARCH", "ENABLE_SEARCH"),
    )
    skill_routing_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("LLM_SKILL_ROUTING_ENABLED", "SKILL_ROUTING_ENABLED"),
    )
    skill_router_model: str = Field(
        default="qwen-turbo",
        validation_alias=AliasChoices("LLM_SKILL_ROUTER_MODEL", "SKILL_ROUTER_MODEL"),
    )
    summary_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("LLM_SUMMARY_ENABLED", "SUMMARY_ENABLED"),
    )
    summary_model: str = Field(
        default="qwen-turbo",
        validation_alias=AliasChoices("LLM_SUMMARY_MODEL", "SUMMARY_MODEL"),
    )
    summary_temperature: float = Field(
        default=0.2,
        validation_alias=AliasChoices("LLM_SUMMARY_TEMPERATURE", "SUMMARY_TEMPERATURE"),
    )
    summary_max_tokens: int = Field(
        default=900,
        validation_alias=AliasChoices("LLM_SUMMARY_MAX_TOKENS", "SUMMARY_MAX_TOKENS"),
    )
    summary_trigger_messages: int = Field(
        default=6,
        validation_alias=AliasChoices("LLM_SUMMARY_TRIGGER_MESSAGES", "SUMMARY_TRIGGER_MESSAGES"),
    )
    context_recent_messages: int = Field(
        default=6,
        validation_alias=AliasChoices("LLM_CONTEXT_RECENT_MESSAGES", "CONTEXT_RECENT_MESSAGES"),
    )
    context_summary_max_chars: int = Field(
        default=1400,
        validation_alias=AliasChoices("LLM_CONTEXT_SUMMARY_MAX_CHARS", "CONTEXT_SUMMARY_MAX_CHARS"),
    )
    baidu_search_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "BAIDU_QIANFAN_API_KEY",
            "QIANFAN_API_KEY",
            "BAIDU_API_KEY",
        ),
    )
    baidu_search_base_url: str = Field(
        default="https://qianfan.baidubce.com",
        validation_alias=AliasChoices(
            "BAIDU_SEARCH_BASE_URL",
            "QIANFAN_BASE_URL",
        ),
    )
    baidu_search_timeout_seconds: float = Field(
        default=30.0,
        validation_alias=AliasChoices(
            "BAIDU_SEARCH_TIMEOUT_SECONDS",
            "QIANFAN_TIMEOUT_SECONDS",
        ),
    )

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()