# Release 13.6

Date: 2026-04-11

Tag: `V13.6`

一句话版本说明：邮件技能补齐收件人缺失拦截、正文质量兜底与联网润色，前端信息分享卡同步展示技能清单并优化关闭交互。

## Scope

- 邮件技能支持优先沿用请求指定模型，并在缺失收件人时返回明确补参提示
- 邮件正文新增低质量识别与二次润色链路，避免将用户指令或标题回声直接发出
- 富信息类邮件请求可触发联网扩写，生成更完整的可发送正文
- 项目信息分享卡改为展示技能清单，并支持保留换行排版
- 信息面板在分享态下优先关闭分享层，避免一次点击直接退出整个弹窗

## Validation

- Backend diagnostics: passed
- Frontend diagnostics: passed
- Frontend production build: passed

## Versioning

- root package version: `13.6.0`
- frontend package version: `13.6.0`
- info panel version text: `V13.6`
- git release target: `V13.6`