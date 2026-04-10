# Release 13.4

Date: 2026-04-11

Tag: `V13.4`

一句话版本说明：邮件发送流程先回归稳定直发，搜索链路从 skill 中拆出，前端统一等待动画反馈。

## Scope

- 邮件发送 skill 切除搜索相关逻辑，仅保留参数补全与 SMTP 发送
- 保留技能元信息中的“实现方式”展示位，便于后续搜索模块独立联调
- 前端 assistant 消息在等待阶段增加打圈加载动画
- 统一连接、路由、技能执行、生成中的等待表现

## Validation

- Backend diagnostics: passed
- Frontend diagnostics: passed
- Local launcher restart: passed

## Versioning

- root package version: `13.4.0`
- frontend package version: `13.4.0`
- info panel version text: `V13.4`
- git release target: `V13.4`
