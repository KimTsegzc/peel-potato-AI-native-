# Release 12.2

Date: 2026-04-09

Tag: `V12.2`

一句话版本说明：继续收口 Info 面板桌面端细节，统一操作区与评论输入区的尺寸、字级和边框表现。

## Scope

- 调整桌面端 Info 操作按钮高度与布局表现
- 统一评论输入框、placeholder、评论正文的字级与行高语言
- 对齐评论输入框与“发布”按钮的外框上下边，收窄整体控件高度
- 同步更新前后端版本元数据与前端版本内容到 `V12.2`

## Highlights

1. 操作区更紧致
- 桌面端“赞 / 转发 / 评论”保持三等分布局，同时将控件高度收窄到更克制的视觉节奏。
- 点赞按钮继续保留数字承载能力，并维持与其余按钮统一的边框语言。

2. 评论输入区对齐正文风格
- 输入框 placeholder 与输入内容改为与评论正文一致的 `13px / 1.5`。
- 输入框与“发布”按钮改为同一套 40px 高度和 box model，消除上下边不齐的问题。

3. 评论区信息表达补齐
- 评论时间统一格式化为 `yy年mm月dd日 hh:mm`。
- 首条固定评论继续展示为版本发布时间，增强信息面板的完成度。

## Validation

- Frontend build: passed

## Versioning

- root package version: `12.2.0`
- frontend package version: `12.2.0`
- info panel version text: `V12.2`
- git release target: `V12.2`