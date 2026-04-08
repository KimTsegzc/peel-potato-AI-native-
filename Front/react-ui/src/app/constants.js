export const API_PORT = 8766;
export const STREAM_PATH = "/api/chat/stream";
export const CONFIG_PATH = "/api/frontend-config";
export const AVATAR_IMAGE_PATH = "/xiexin-avatar.png";
export const AVATAR_INTERACTION_VIDEO_PATH = "/smile%20face.mp4";
export const MOBILE_BREAKPOINT = 900;
export const SESSION_STORAGE_KEY = "xiexin.chat.session.v1";
export const MAX_PERSISTED_MESSAGES = 48;
export const PROJECT_INFO = {
	projectName: "谢鑫的智能体",
	developer: "广分金科部",
	version: "V10.1",
	features: [
		"按当前时间和时段生成问候，避免早晚问候错位。",
		"支持多轮上下文记忆，融合 recent turns 与增量 summary。",
		"支持实时流式回复，并保留搜索增强与调试链路。",
	],
	versionChange: "本版本重点修复欢迎语在微信端与移动 Chrome 的断行频闪，并同步细化项目信息面板展示。",
};
