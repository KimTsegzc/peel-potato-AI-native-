export const API_PORT = 8766;
export const STREAM_PATH = "/api/chat/stream";
export const CONFIG_PATH = "/api/frontend-config";
export const INFO_REACTIONS_BASE_PATH = "/api/info";
export const PROJECT_INFO_ID = "project-info-v134";
export const AVATAR_IMAGE_PATH = "/xiexin-avatar.png";
export const AVATAR_INTERACTION_VIDEO_PATH = "/smile%20face.mp4";
export const MOBILE_BREAKPOINT = 900;
export const SESSION_STORAGE_KEY = "xiexin.chat.session.v1";
export const MAX_PERSISTED_MESSAGES = 48;
export const PROJECT_INFO = {
	projectName: "谢鑫的智能体",
	developer: "广分金科部",
	version: "V13.4",
	releaseTime: "2026-04-11T03:15:00+08:00",
	features: [
		"邮件发送 skill 切除搜索链路，回归稳定直发流程。",
		"保留技能元信息实现方式展示，便于后续搜索模块单独联调。",
		"聊天回复在等待阶段新增打圈加载动画，统一等待体验。",
	],
	info: "面向工作场景的企业智能问答与信息检索助手。",
	versionChange: "收敛邮件发送路径并统一前端加载反馈。",
};
