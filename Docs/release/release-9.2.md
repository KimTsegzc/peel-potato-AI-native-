# Release 9.2

Date: 2026-04-06

Tag: `V9.2`

一句话版本说明：修复 chat 页面 New Chat 后欢迎语不刷新的问题，改为新建会话时强制刷新欢迎语配置并重置 welcome session id。

## Scope

- new chat event wiring fix
- welcome session id reset on new chat
- frontend-config active refresh support
- version bump and release notes

## Problem

- 在 chat 页面点击 New Chat 仅清空消息会话，未重新拉取 `/api/frontend-config`。
- `xiexin.welcome.session.id` 也未重置，导致欢迎语可能沿用同一会话记忆与同一展示文本，看起来“新建会话欢迎语不变”。

## Fix

1. `useFrontendConfig` 支持主动刷新
- 文件：`Front/react-ui/src/app/hooks/useFrontendConfig.js`
- 新增 `refreshFrontendConfig()`，可在非初始化阶段手动触发 config 重新获取。

2. `New Chat` 时重置 welcome session id
- 文件：`Front/react-ui/src/app/utils/api.js`
- 新增 `resetWelcomeSessionId()`，生成并写入新的 `xiexin.welcome.session.id`。

3. App 的 New Chat 事件串联刷新链路
- 文件：`Front/react-ui/src/App.jsx`
- `handleNewChat` 改为：
  - reset chat session
  - reset welcome session id
  - refresh frontend config
  - 触发 hero typing seed

## Validation

- Frontend lint/type diagnostics: no new errors
- Frontend build: passed (`vite build`)
- Python compile check: passed (`orchestrator.py Backend apps Prompt`)

## Versioning

- root package version: `9.2.0`
- frontend package version: `9.2.0`
- git release target: `V9.2`
