import { useEffect, useRef, useState } from "react";

const HERO_TEXT = "我是鑫哥，帮你搞搞数据";
const API_PORT = 8765;
const STREAM_PATH = "/api/chat/stream";
const CONFIG_PATH = "/api/frontend-config";

function resolveApiBase() {
  const { protocol, hostname } = window.location;
  const safeProtocol = protocol === "https:" ? "https:" : "http:";
  return `${safeProtocol}//${hostname}:${API_PORT}`;
}

function renderInlineMarkdown(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/__([^_]+)__/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/_([^_]+)_/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer noopener">$1</a>');
}

function renderMarkdown(markdownText) {
  const source = String(markdownText || "").replace(/\r\n/g, "\n");
  const blocks = source.split(/\n\n+/).filter(Boolean);
  return blocks
    .map((block) => {
      if (/^#{1,6}\s/.test(block)) {
        const match = block.match(/^(#{1,6})\s+(.*)$/);
        const level = match[1].length;
        return `<h${level}>${renderInlineMarkdown(match[2])}</h${level}>`;
      }
      if (/^[-*+]\s/m.test(block)) {
        const items = block
          .split("\n")
          .filter(Boolean)
          .map((item) => item.replace(/^[-*+]\s+/, ""))
          .map((item) => `<li>${renderInlineMarkdown(item)}</li>`)
          .join("");
        return `<ul>${items}</ul>`;
      }
      return `<p>${renderInlineMarkdown(block).replace(/\n/g, "<br />")}</p>`;
    })
    .join("");
}

function Metrics({ metrics }) {
  if (!metrics) return null;
  const firstToken = metrics.first_token_latency_seconds != null
    ? `${metrics.first_token_latency_seconds.toFixed(1)}s`
    : "N/A";
  const total = metrics.latency_seconds != null ? `${metrics.latency_seconds.toFixed(1)}s` : "N/A";
  return <div className="message-meta">模型: {metrics.model || "N/A"} | 首 token: {firstToken} | 总耗时: {total}</div>;
}

function MessageBubble({ message }) {
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

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [activeModelIndex, setActiveModelIndex] = useState(-1);
  const [settingsAnchor, setSettingsAnchor] = useState("header");
  const [chatMode, setChatMode] = useState(false);
  const [statusText, setStatusText] = useState(HERO_TEXT);
  const [configReady, setConfigReady] = useState(false);
  const threadRef = useRef(null);
  const textareaRef = useRef(null);
  const headerSettingsRef = useRef(null);
  const railSettingsRef = useRef(null);
  const apiBase = resolveApiBase();

  function getPreferredSettingsAnchor() {
    return chatMode && window.innerWidth > 900 ? "rail" : "header";
  }

  function toggleSettings(anchor) {
    setSettingsAnchor(anchor);
    setSettingsOpen((current) => (settingsAnchor === anchor ? !current : true));
  }

  useEffect(() => {
    const root = document.documentElement;

    function syncViewportMetrics() {
      const viewport = window.visualViewport;
      const viewportHeight = viewport?.height || window.innerHeight;
      const keyboardOffset = Math.max(0, window.innerHeight - viewportHeight - (viewport?.offsetTop || 0));
      root.style.setProperty("--app-height", `${viewportHeight}px`);
      root.style.setProperty("--keyboard-offset", `${keyboardOffset}px`);
    }

    syncViewportMetrics();
    window.addEventListener("resize", syncViewportMetrics);
    window.visualViewport?.addEventListener("resize", syncViewportMetrics);
    window.visualViewport?.addEventListener("scroll", syncViewportMetrics);

    return () => {
      window.removeEventListener("resize", syncViewportMetrics);
      window.visualViewport?.removeEventListener("resize", syncViewportMetrics);
      window.visualViewport?.removeEventListener("scroll", syncViewportMetrics);
    };
  }, []);

  useEffect(() => {
    let active = true;
    fetch(`${apiBase}${CONFIG_PATH}`)
      .then((response) => response.json())
      .then((config) => {
        if (!active) return;
        const nextModels = Array.isArray(config.availableModels) ? config.availableModels : [];
        const nextSelectedModel = config.defaultModel || nextModels[0] || "";
        setModels(nextModels);
        setSelectedModel(nextSelectedModel);
        setActiveModelIndex(Math.max(0, nextModels.indexOf(nextSelectedModel)));
        setConfigReady(true);
      })
      .catch(() => {
        if (!active) return;
        setModels([]);
        setSelectedModel("");
        setConfigReady(true);
      });
    return () => {
      active = false;
    };
  }, [apiBase]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      let index = 0;
      const timer = window.setInterval(() => {
        index += 1;
        setStatusText(HERO_TEXT.slice(0, index) || HERO_TEXT);
        if (index >= HERO_TEXT.length) {
          window.clearInterval(timer);
        }
      }, 45);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (!threadRef.current) return;
    threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "0px";
    const nextHeight = Math.min(textareaRef.current.scrollHeight, 136);
    textareaRef.current.style.height = `${nextHeight}px`;
  }, [input]);

  useEffect(() => {
    if (!configReady || loading || settingsOpen) return undefined;

    const frame = requestAnimationFrame(() => {
      textareaRef.current?.focus();
    });

    return () => window.cancelAnimationFrame(frame);
  }, [configReady, loading, settingsOpen]);

  useEffect(() => {
    if (!settingsOpen) return undefined;

    function handlePointerDown(event) {
      const insideHeader = headerSettingsRef.current?.contains(event.target);
      const insideRail = railSettingsRef.current?.contains(event.target);
      if (!insideHeader && !insideRail) {
        setSettingsOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [settingsOpen]);

  useEffect(() => {
    if (!settingsOpen) return;
    const selectedIndex = models.indexOf(selectedModel);
    setActiveModelIndex(selectedIndex >= 0 ? selectedIndex : 0);
  }, [settingsOpen, models, selectedModel]);

  useEffect(() => {
    function handleGlobalKeyDown(event) {
      if (event.isComposing || event.repeat) return;

      if (event.altKey && !event.ctrlKey && !event.metaKey && event.key.toLowerCase() === "s") {
        event.preventDefault();
        const nextAnchor = getPreferredSettingsAnchor();
        setSettingsAnchor(nextAnchor);
        setSettingsOpen((current) => (settingsAnchor === nextAnchor ? !current : true));
        return;
      }

      if (!settingsOpen) return;

      if (event.key === "Escape") {
        event.preventDefault();
        setSettingsOpen(false);
        textareaRef.current?.focus();
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveModelIndex((current) => {
          if (!models.length) return -1;
          return current < 0 ? 0 : (current + 1) % models.length;
        });
        return;
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveModelIndex((current) => {
          if (!models.length) return -1;
          return current < 0 ? models.length - 1 : (current - 1 + models.length) % models.length;
        });
        return;
      }

      if (event.key === "Enter") {
        const nextModel = models[activeModelIndex];
        if (!nextModel) return;
        event.preventDefault();
        setSelectedModel(nextModel);
        setSettingsOpen(false);
        textareaRef.current?.focus();
      }
    }

    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, [activeModelIndex, chatMode, models, settingsAnchor, settingsOpen]);

  function renderSettingsControl(anchor) {
    const anchorRef = anchor === "header" ? headerSettingsRef : railSettingsRef;
    const popoverOpen = settingsOpen && settingsAnchor === anchor;

    return (
      <div className="topbar-actions" ref={anchorRef}>
        <button
          className={`settings-toggle ${popoverOpen ? "is-open" : ""}`}
          type="button"
          onClick={() => toggleSettings(anchor)}
          aria-label="切换模型设置"
        >
          <span />
          <span />
          <span />
        </button>
        {popoverOpen ? (
          <div className="settings-popover">
            <div className="settings-title">选择模型</div>
            <div className="settings-list">
              {models.map((model, index) => (
                <button
                  key={model}
                  type="button"
                  className={`settings-option ${selectedModel === model ? "is-selected" : ""} ${activeModelIndex === index ? "is-active" : ""}`}
                  onMouseEnter={() => setActiveModelIndex(index)}
                  onClick={() => {
                    setSelectedModel(model);
                    setSettingsOpen(false);
                    textareaRef.current?.focus();
                  }}
                >
                  {model}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  function handleComposerKeyDown(event) {
    if (event.isComposing) return;
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  async function handleSubmit(event) {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMessage = { role: "user", content: trimmed };
    const assistantIndex = messages.length + 1;
    setChatMode(true);
    setSettingsOpen(false);
    setMessages((current) => [
      ...current,
      userMessage,
      { role: "assistant", content: "正在连接服务...", metrics: null },
    ]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${apiBase}${STREAM_PATH}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_input: trimmed,
          smooth: true,
          model: selectedModel || undefined,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let assistantText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        lines.forEach((rawLine) => {
          const line = rawLine.trim();
          if (!line) return;
          const eventPayload = JSON.parse(line);

          if (eventPayload.type === "pulse") {
            const pulseText = eventPayload.stage === "accepted" ? "正在连接模型..." : "正在生成回复...";
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex ? { ...message, content: pulseText } : message
            )));
          }

          if (eventPayload.type === "delta") {
            assistantText += eventPayload.content || "";
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex ? { ...message, content: assistantText } : message
            )));
          }

          if (eventPayload.type === "done") {
            assistantText = eventPayload.content || assistantText;
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex
                ? { ...message, content: assistantText, metrics: eventPayload.metrics || null }
                : message
            )));
          }

          if (eventPayload.type === "error") {
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex
                ? { ...message, content: `请求失败：${eventPayload.message || "unknown error"}` }
                : message
            )));
          }
        });
      }
    } catch (error) {
      setMessages((current) => current.map((message, index) => (
        index === assistantIndex
          ? { ...message, content: `请求失败：${error.message || error}` }
          : message
      )));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`app-shell ${chatMode ? "chat-mode" : "welcome-mode"}`}>
      <header className="topbar">
        {renderSettingsControl("header")}
      </header>

      {!chatMode ? (
        <section className="hero-panel">
          <img className="hero-avatar" src="/xiexin-avatar.png" alt="鑫哥头像" />
          <div className="hero-copy">
            <h1 className="hero-title">{statusText}</h1>
          </div>
        </section>
      ) : null}

      <main className="chat-stage">
        {chatMode ? (
          <aside className="chat-rail" aria-hidden="true">
            <div className="chat-rail-inner">
              <img className="chat-rail-avatar" src="/xiexin-avatar.png" alt="" />
              <div className="chat-rail-settings">{renderSettingsControl("rail")}</div>
            </div>
          </aside>
        ) : null}
        <section className="chat-surface" ref={threadRef}>
          {messages.map((message, index) => <MessageBubble key={`${message.role}-${index}`} message={message} />)}
        </section>
      </main>

      <form className="composer-shell" onSubmit={handleSubmit}>
        <div className={`composer-box ${input.trim() ? "has-text" : "is-empty"}`}>
          <div className="composer-leading">
            <div className="composer-model">{selectedModel || "model"}</div>
          </div>
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleComposerKeyDown}
            placeholder="Ask anything"
            disabled={!configReady || loading}
            autoFocus
          />
          <button type="submit" className="send-button" disabled={!configReady || loading}>
            {loading ? "..." : "➤"}
          </button>
        </div>
      </form>
    </div>
  );
}
