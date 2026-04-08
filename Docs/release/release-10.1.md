# Release 10.1

Date: 2026-04-08

Tag: `V10.1`

一句话版本说明：聚焦欢迎语渲染稳定性与信息面板细节优化，收敛移动端首屏断行频闪问题。

## Scope

- welcome title rendering stabilization on WeChat and mobile Chrome
- info panel content refinement and typography cleanup
- patch version metadata update

## Highlights

1. 欢迎语渲染稳定性修复
- 欢迎语标题改为隐藏测量后再显示最终布局，避免先单行再断行的可见闪烁。
- 对同一句欢迎语锁定多行判定，减少微信 WebView 视口波动时的来回重排。

2. 信息面板内容与排版收敛
- “主要功能”更新为当前系统真实支持能力。
- 新增“版本变更”摘要，统一正文字号并缩小段落间距。

## Validation

- Frontend diagnostics: no new errors
- Modified files syntax check: passed

## Versioning

- root package version: `10.1.0`
- frontend package version: `10.1.0`
- info panel version text: `V10.1`
- git release target: `V10.1`