# Backend Architecture

## Goal

`Backend` 是后端核心实现目录，职责分为四层：

- `features/`：APP 业务功能层，承载会话上下文、互动状态、业务规则、功能级存储与校验。
- `runtime/`：智能体运行时与编排层，只处理请求契约、技能注册、技能路由、执行调度。
- `integrations/`：所有外部能力接入层，负责对第三方 SDK、HTTP API、SMTP、文件解析、TTS/ASR/OCR 等做封装。
- `settings.py` 与少量共享模块：配置读取、上下文准备、通用状态处理。

这个分层的核心规则是：

- 运行时不直接散落第三方协议细节。
- APP 功能实现优先放在 `features/`，不要继续把业务模块平铺在 `Backend/` 根目录。
- 新增外部能力时，优先落到 `integrations/`，不要继续把实现铺在 `Backend/` 根目录。
- 外部能力实现统一放在 `integrations/`，不再在 `Backend/` 根目录保留 provider shim。

## Current Layout
‘
- `features/conversation_context.py`：会话历史、滚动摘要、上下文拼装。
- `features/info_reactions.py`：点赞、评论、互动查询等 APP 互动功能。
- `runtime/`：技能执行壳层，负责路由与调度。
- `integrations/llm_provider.py`：LLM 调用与流式输出。
- `integrations/search_provider.py`：百度千帆搜索集成。
- `integrations/email_sender.py`：SMTP 邮件发送。
- `settings.py`：统一 `.env` 配置入口，以及按能力切片的 accessor。

## Design Rules

### 1. Runtime only orchestrates

`runtime/` 里可以依赖 `LLMProvider` 这类统一入口，但不要把第三方 SDK 调用细节、鉴权、HTTP 请求体拼装直接写进 runtime。

### 2. One capability, one integration module

新增能力时，优先按下面方式组织：

- `integrations/file_processing.py`
- `integrations/tts_provider.py`
- `integrations/asr_provider.py`
- `integrations/ocr_provider.py`

每个模块建议至少包含：

- 一个函数式入口
- 一个 facade class
- 清晰的错误类型
- 一个可独立调试的 `main()` CLI

### 3. One app feature, one feature module

像会话上下文、点赞评论、上传记录、欢迎态缓存这类“APP 功能实现”，不属于 integration，也不属于 runtime，应该进入 `features/`。

当前推荐方式：

- 小功能先用单文件模块，例如 `features/info_reactions.py`
- 一旦某个功能开始出现多种存储、DTO、service、policy，就升级为子目录模块，例如：
	`features/chat_context/__init__.py`
	`features/chat_context/service.py`
	`features/chat_context/store.py`
	`features/chat_context/contracts.py`

判断标准很简单：

- 是否在实现产品功能，而不是接三方能力：放 `features/`
- 是否在封装外部 SDK / API / SMTP / OCR / TTS：放 `integrations/`
- 是否在做技能调度和执行编排：放 `runtime/`

### 4. Narrow config access

不要让每个调用方都直接读取整份 `Settings`。优先在 `settings.py` 里提供能力级 accessor，例如：

- `get_llm_settings()`
- `get_search_settings()`
- `get_email_settings()`

这样后续配置变多时，调用面不会越来越散。

### 5. Import rules

外部能力导入统一使用：

- `Backend.integrations.llm_provider`
- `Backend.integrations.search_provider`
- `Backend.integrations.email_sender`

或：

- `Backend.integrations`

APP 功能导入统一使用：

- `Backend.features.conversation_context`
- `Backend.features.info_reactions`

或：

- `Backend.features`

## Recommended Pattern For New Integrations

新增集成能力时，建议遵守下面的最小模板：

1. 在 `settings.py` 增加必要配置。
2. 如果配置较多，补一个 capability settings dataclass 与 accessor。
3. 在 `integrations/` 新建实现模块。
4. 定义明确的异常类型，避免直接向上抛裸异常。
5. 提供 facade class，供 runtime 或 API 层调用。
6. 如果适合独立调试，补一个 `main()`。
7. 不要在 `Backend/` 根目录再新增 provider shim。

## File Processing And TTS Guidance

后续要接入文件处理和 TTS，建议按这个边界执行：

- 轻量文本提取、格式转换、上传后解析：可以先放在 `integrations/` 内同步实现。
- 大文件解析、OCR、音频生成、长耗时转码：不要直接阻塞主请求线程，最好单独抽成任务式执行或后台 worker。
- 文件路径、临时文件、缓存目录不要散落到各模块，后续建议统一抽成一个存储/工作目录策略模块。

## Professional Implementation Notes

更专业的做法不是把所有后端代码都塞进 `services/`，而是按职责分层：

- `apps/api`：接口层，负责 HTTP 协议和请求响应。
- `Backend/runtime`：智能体编排层。
- `Backend/features`：产品功能层。
- `Backend/integrations`：外部能力接入层。
- `Backend/settings.py`：配置与 capability accessor。

这样做的收益是：

- 产品功能和外部依赖解耦。
- 后续接文件处理、TTS、ASR、OCR 时，不会把业务逻辑污染掉。
- 某个 APP 功能扩展时，可以单独演进成 feature package，而不用推倒整个 Backend 结构。

## Import Preference

新代码的推荐导入顺序：

1. `from Backend.features import ...` 或 `from Backend.features.xxx import ...`
2. `from Backend.integrations import ...` 或 `from Backend.integrations.xxx import ...`
3. `from Backend.runtime import ...` 仅用于编排入口
4. 不要新增 `from Backend.xxx import ...` 这类根目录平铺导入

## Summary

后续扩展时，把 `Backend` 看成“功能层 + 编排层 + 集成层 + 配置层”，而不是“所有后端代码的平铺目录”。
只要坚持 `features / runtime / integrations` 分层，后面继续加文件处理、TTS、邮件、搜索和互动功能，不需要每次回头做结构性重构。