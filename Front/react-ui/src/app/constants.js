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
	version: "V11.0",
	features: [
		"支持基于大模型 tool calling 的主路由，由 qwen-turbo 选择最合适的技能。",
		"新增分行职能负责人查询技能，可按工作职责匹配部门、岗位、负责人链条与办公号码。",
		"负责人链条输出带职务，并附带岗位职责摘要与更自然的回复开场。",
	],
	versionChange: "本版本新增 LLM 主路由、职能表技能查询链路与技能说明书能力，并同步调整 info 面板内容顺序与版本信息。",
};
