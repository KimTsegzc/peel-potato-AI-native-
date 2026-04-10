export const API_PORT = 8766;
export const STREAM_PATH = "/api/chat/stream";
export const CONFIG_PATH = "/api/frontend-config";
export const INFO_REACTIONS_BASE_PATH = "/api/info";
export const PROJECT_INFO_ID = "project-info-v132";
export const AVATAR_IMAGE_PATH = "/xiexin-avatar.png";
export const AVATAR_INTERACTION_VIDEO_PATH = "/smile%20face.mp4";
export const MOBILE_BREAKPOINT = 900;
export const SESSION_STORAGE_KEY = "xiexin.chat.session.v1";
export const MAX_PERSISTED_MESSAGES = 48;
export const PROJECT_INFO = {
	projectName: "谢鑫的智能体",
	developer: "广分金科部",
	version: "V13.2",
	releaseTime: "2026-04-11T02:05:00+08:00",
	features: [
		"新增邮件发送技能链路：前端指令可路由到后端邮件能力。",
		"新增技能调用可视化提示，并隐藏通用对话技能噪音展示。",
		"邮件 SMTP 失败时新增 turbo 二次解释，返回可执行修复建议。",
	],
	info: "面向工作场景的企业智能问答与信息检索助手。",
	versionChange: "增强邮件失败可解释性，降低用户排障成本。",
};
