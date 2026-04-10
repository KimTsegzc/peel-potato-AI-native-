# Release 13.0

Date: 2026-04-11

Tag: `V13`

一句话版本说明：打通邮件技能闭环，补齐技能调用可视化与路由可靠性，保证“说到就执行”。

## Scope

- 新增邮件发送 skill，支持从前端指令路由到后端 SMTP 发送能力
- 技能体系按“一技能一目录”整理，统一 SKILL.md 规范
- 增加 skill selected 流事件，前端展示“正在调用xx技能”
- 对发邮件意图增加规则快路径，降低误落通用对话的概率
- 缺参场景加入 qwen-turbo 结构化适配，提升邮件请求容错
- 前端消息元信息改为有值才显示，移除 N/A 噪音

## Validation

- Backend health: passed
- Frontend health: passed
- 邮件技能链路联调: passed

## Versioning

- root package version: `13.0.0`
- frontend package version: `13.0.0`
- info panel version text: `V13`
- git release target: `V13`
