---
name: skill-direct-chat
description: 'Use when handling general chat, open-domain Q&A, greetings, or requests that do not match a specialized business skill.'
---

# Direct Chat Skill

## Purpose
通用对话兜底技能，处理闲聊、开放问答，以及不适合交给专门业务技能的问题。

## Use When
- 用户在打招呼、闲聊、问通用知识或生活类问题。
- 用户的问题不是在问分行内部哪个部门、岗位、负责人承接某项工作。
- 用户的问题指向外部机构、外部客服电话、泛建议，而不是行内职能分工。

## Avoid When
- 用户明确在问分行内部职能分工、行内接口人、岗位负责人、办公号码。
- 用户明确要求执行动作型技能，例如发送邮件。

## Input Contract
- 输入为标准 `AgentRequest`。
- 主要消费 `user_input`、`session_id`、`model`、`smooth`。

## Output Contract
- 输出标准 `AgentResponse` 或流式事件。
- 结果由 LLM 直接生成，不进行业务结构化改写。

## Runtime Notes
- 该技能是默认兜底技能。
- 路由不确定时应优先落到本技能，避免误命中业务技能。
