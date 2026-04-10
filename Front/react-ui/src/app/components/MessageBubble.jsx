import { renderMarkdown } from "../utils/markdown";

function Metrics({ metrics }) {
  if (!metrics) return null;
  const firstToken = metrics.first_token_latency_seconds != null
    ? `${metrics.first_token_latency_seconds.toFixed(1)}s`
    : "";
  const total = metrics.latency_seconds != null ? `${metrics.latency_seconds.toFixed(1)}s` : "";
  const selectedSkill = metrics.routing?.selected_skill_label || metrics.routing?.selected_skill || "";
  const selectedSkillName = metrics.routing?.selected_skill || "";
  const showSkill = Boolean(selectedSkill) && selectedSkillName !== "direct_chat" && selectedSkill !== "通用对话";
  const modelName = metrics.model || "";
  const parts = [];

  if (modelName) parts.push(`模型: ${modelName}`);
  if (showSkill) parts.push(`技能: ${selectedSkill}`);
  if (firstToken) parts.push(`首 token: ${firstToken}`);
  if (total) parts.push(`总耗时: ${total}`);

  if (!parts.length) return null;

  return <div className="message-meta">{parts.join(" | ")}</div>;
}

export function MessageBubble({ message }) {
  return (
    <div className={`message-row ${message.role}`}>
      <div className="message-bubble">
        {message.role === "assistant" ? (
          <div className="message-content" dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
        ) : (
          <div className="message-content">{message.content}</div>
        )}
        <Metrics metrics={message.metrics} />
      </div>
    </div>
  );
}
