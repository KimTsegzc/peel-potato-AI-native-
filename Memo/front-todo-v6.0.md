# Front TODO for v6.0

Date: 2026-03-27

## Current Conclusion
- 微信端输入法问题已基本压住，当前封板版本的主要剩余风险不在微信端。
- 除微信端外，移动端浏览器输入法弹起导致的顶飞问题依然严重，尤其是 `is-mobile-default` 路径。

## Remaining Issue
- 输入法弹起时，顶部固定元素仍可能被整体上推，表现为头像、设置按钮、顶部区被“顶飞”
- 输入框与消息输出区之间仍可能出现不合理空隙或悬浮错位
- 不同 Android 浏览器对 `visualViewport`、页面自动滚动、软键盘占位的处理差异仍然大

## Current Implementation
- 页面已按 desktop / mobile-default / wechat 拆壳
- 移动端壳层使用固定容器，聊天态改为稳定高度壳层，内部通过 `--keyboard-offset` 迁移 composer 与 thread surface
- 视口同步集中在 `useViewportMetrics`，通过 `window.resize`、`orientationchange`、`visualViewport.resize` 驱动 CSS 变量
- 页面滚动锁通过 `useAppScrollLock` 处理，输入法焦点进入后执行延迟 `scrollTo(0, 0)`
- 线程滚动、键盘收起、textarea 自增高已拆成独立 hooks 管理

## Tried So Far
- 去掉一部分 `visualViewport.scroll` 驱动，减少 viewport 写入和 scroll lock 互相打架
- 把移动端 composer 从依赖 viewport 的 `fixed` 思路改到壳层内部绝对定位
- 引入稳定高度变量 `--app-height-stable`，避免 chat shell 随输入法直接缩放
- 用聚焦冻结窗口和延迟重算，降低 Android Chrome / Edge 首次弹键盘时的抖动峰值
- 欢迎态改成完全静止，避免欢迎页元素随键盘整体上移
- 增加 `keyboardOffset` 的焦点门控和阈值门控，避免欢迎态切聊天态时输入框悬空

## Why It Is Still Not Solved
- 非微信移动端浏览器对 `visualViewport`、自动滚动、焦点恢复和地址栏联动的时序不稳定
- 当前方案仍是“稳定壳层 + 运行时补偿”，本质上还是在对抗浏览器行为，而不是拿到真正统一的软键盘状态源
- `thread auto scroll`、viewport 更新、focus/blur 回调之间仍存在竞争窗口

## Priority After Release
1. 真实设备上逐浏览器复测 Android Chrome / Edge / 厂商 WebView
2. 明确是否要为非微信移动端单独建立 keyboard state 机理，不再强行和微信端共享策略
3. 若现有补偿链路继续不稳，考虑进一步收敛为“页面不缩壳，只移动输入层”的单一路径