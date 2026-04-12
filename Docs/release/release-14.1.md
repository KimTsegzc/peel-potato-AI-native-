# Release 14.1

Date: 2026-04-12

Tag: `V14.1`

一句话版本说明：补齐生产环境上传体积限制，修复欢迎页首问带图上传的 `HTTP 413`，并完善上传失败提示。

## Scope

- nginx 模板新增 `client_max_body_size 16m;`，支持生产环境图片/文件上传
- 前端上传接口对 `HTTP 413` 给出明确中文提示，不再只显示裸状态码
- 本轮发版包含此前已落地的上传能力、omni 模型小写修正与移动端上传入口恢复

## Validation

- Frontend production build: passed
- CI/CD trigger mode: push to `main`
- Production deploy config updated: passed

## Versioning

- root package version: `14.1.0`
- frontend package version: `14.1.0`
- info panel version text: `V14.1`
- git release target: `V14.1`