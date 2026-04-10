export const API_PORT = 8766;
export const STREAM_PATH = "/api/chat/stream";
export const CONFIG_PATH = "/api/frontend-config";
export const INFO_REACTIONS_BASE_PATH = "/api/info";
export const PROJECT_INFO_ID = "project-info-v136";
export const AVATAR_IMAGE_PATH = "/xiexin-avatar.png";
export const AVATAR_INTERACTION_VIDEO_PATH = "/smile%20face.mp4";
export const MOBILE_BREAKPOINT = 900;
export const SESSION_STORAGE_KEY = "xiexin.chat.session.v1";
export const MAX_PERSISTED_MESSAGES = 48;
export const PROJECT_SKILL_SET = [
	"skill-direct-chat",
	"skill-ccb-get-handler",
	"skill-send-email",
];
export const PROJECT_INFO = {
	projectName: "谢鑫的智能体",
	developer: "广分金科部",
	version: "V13.6",
	releaseTime: "2026-04-11T12:20:00+08:00",
	features: [
		"邮件技能补齐收件人缺失拦截、正文质量判定与自动润色补全。",
		"富文本邮件请求支持按需联网扩写，避免把用户指令原样发出。",
		"项目信息分享卡新增技能清单展示，分享面板关闭逻辑更顺手。",
	],
	info: "面向工作场景的企业智能问答与信息检索助手。",
	versionChange: "增强邮件技能成稿能力，并补齐信息面板分享卡展示。",
};
