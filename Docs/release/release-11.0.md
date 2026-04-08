# Release 11.0

Date: 2026-04-09

Tag: `V11.0`

一句话版本说明：引入基于大模型 tool calling 的主路由，并新增分行职能负责人查询技能，补齐技能说明书与更结构化的内部职责回复链路。

## Scope

- LLM-first skill routing with tool calling via qwen-turbo
- new CCB internal handler lookup skill and business table runtime integration
- enriched handler response format with chain titles and responsibility summary
- info panel reorder and version metadata refresh

## Highlights

1. LLM 主路由接管技能选择
- runtime router 改为由大模型通过 tool calling 选择目标 skill。
- 清除针对单个 skill 的关键词快脑，LLM 成为唯一技能选择器。
- 路由失败时仅回退到默认 `direct_chat`，不再存在字符串命中某个业务 skill 的捷径。

2. 新增分行职能负责人查询能力
- 新增 `skill_ccb_get_handler`，基于分行职能表按工作职责匹配对应部门、岗位与负责人。
- 技能查询链路支持输出部门、岗位、负责人链条、办公号码，并附带岗位职责摘要。
- 职能表脱敏字符在 skill 数据层统一归一为 `x`，避免前端渲染吞掉 `*`。

3. 技能规范与回复体验升级
- 为 runtime skill 增加 metadata 描述能力，并补充 `SKILL.md` 说明书。
- 职能查询回复增加更自然的开场白，并在负责人链条中带出职务信息。
- info 面板将“主要功能”调整到“版本变更”之前，版本文案同步到 `V11.0`。

## Validation

- Python modified files static errors: passed
- Router fallback behavior check: passed
- Handler response formatting sample: passed
- Live backend smoke test: passed before final version metadata update

## Versioning

- root package version: `11.0.0`
- frontend package version: `11.0.0`
- info panel version text: `V11.0`
- git release target: `V11.0`