# Release 13.2

Date: 2026-04-11

Tag: `V13.2`

一句话版本说明：邮件发送失败时新增 turbo 二次解释，让用户直接看到问题原因和修复动作。

## Scope

- 扩展 `send_email` skill 失败处理分支
- SMTP 报错时再次调用 `qwen-turbo`，输出中文可执行解释
- 针对收件人格式错误（如缺少 `@domain`）给出明确提示和示例
- 保留原始 SMTP 错误，便于运维定位
- 同步版本号到 `V13.2`

## Validation

- Python syntax check: passed
- Version metadata consistency: passed

## Versioning

- root package version: `13.2.0`
- frontend package version: `13.2.0`
- info panel version text: `V13.2`
- git release target: `V13.2`
