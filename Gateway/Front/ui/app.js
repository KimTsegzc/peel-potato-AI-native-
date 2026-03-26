const heroTitleEl = document.getElementById("hero-title");
const heroTextEl = document.getElementById("hero-text");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const pageEl = document.querySelector(".page");
const chatShellEl = document.getElementById("chat-shell");
const settingsPanelEl = document.getElementById("settings-panel");
const settingsToggleEl = document.getElementById("settings-toggle");
const modelOptionsEl = document.getElementById("model-options");
const streamApiUrl = window.APP_CONFIG?.streamApiUrl;
const availableModels = Array.isArray(window.APP_CONFIG?.availableModels)
  ? window.APP_CONFIG.availableModels.filter((model) => typeof model === "string" && model.trim())
  : [];
const defaultModel = typeof window.APP_CONFIG?.defaultModel === "string"
  ? window.APP_CONFIG.defaultModel.trim()
  : "";
const modelStorageKey = typeof window.APP_CONFIG?.modelStorageKey === "string"
  ? window.APP_CONFIG.modelStorageKey
  : "xiexin-da-agent.selected-model";

const fullTitle = (heroTitleEl && heroTitleEl.dataset.fulltext) || "";
let titleIndex = 0;
let hasEnteredChatMode = false;
let requestInFlight = false;
let selectedModel = "";
let isSettingsOpen = false;

function isKnownModel(model) {
  return Boolean(model) && availableModels.includes(model);
}

function readStoredModel() {
  try {
    return window.localStorage.getItem(modelStorageKey) || "";
  } catch (error) {
    return "";
  }
}

function writeStoredModel(model) {
  try {
    if (model) {
      window.localStorage.setItem(modelStorageKey, model);
      return;
    }
    window.localStorage.removeItem(modelStorageKey);
  } catch (error) {
    // Ignore storage failures and continue with in-memory state.
  }
}

function getFallbackModel() {
  if (isKnownModel(defaultModel)) return defaultModel;
  if (availableModels.length > 0) return availableModels[0];
  return "";
}

function resolveSelectedModel() {
  const storedModel = readStoredModel();
  if (isKnownModel(storedModel)) {
    return storedModel;
  }

  if (storedModel) {
    writeStoredModel("");
  }

  return getFallbackModel();
}

function populateModelOptions() {
  if (!modelOptionsEl) return;

  modelOptionsEl.innerHTML = "";

  if (availableModels.length === 0) {
    const emptyState = document.createElement("button");
    emptyState.type = "button";
    emptyState.className = "settings-option";
    emptyState.textContent = "No models available";
    emptyState.disabled = true;
    modelOptionsEl.appendChild(emptyState);
    return;
  }

  availableModels.forEach((model) => {
    const optionButton = document.createElement("button");
    optionButton.type = "button";
    optionButton.className = "settings-option";
    optionButton.textContent = model;
    optionButton.dataset.model = model;
    optionButton.setAttribute("role", "option");
    optionButton.setAttribute("aria-selected", String(model === selectedModel));
    if (model === selectedModel) {
      optionButton.classList.add("is-selected");
    }
    modelOptionsEl.appendChild(optionButton);
  });
}

function setSettingsOpen(open) {
  isSettingsOpen = Boolean(open);
  if (settingsPanelEl) {
    settingsPanelEl.classList.toggle("is-open", isSettingsOpen);
  }
  if (settingsToggleEl) {
    settingsToggleEl.setAttribute("aria-expanded", String(isSettingsOpen));
    settingsToggleEl.setAttribute("aria-label", isSettingsOpen ? "收起设置" : "打开设置");
  }
}

function setModelSelectEnabled(enabled) {
  if (!modelOptionsEl) return;
  const optionButtons = modelOptionsEl.querySelectorAll(".settings-option");
  if (optionButtons.length === 0) {
    return;
  }
  optionButtons.forEach((button) => {
    button.disabled = !enabled;
  });
}

function initializeModelSettings() {
  selectedModel = resolveSelectedModel();
  populateModelOptions();
  setModelSelectEnabled(true);
  setSettingsOpen(false);

  if (settingsToggleEl) {
    settingsToggleEl.addEventListener("click", function () {
      setSettingsOpen(!isSettingsOpen);
    });
  }

  document.addEventListener("click", function (event) {
    if (!isSettingsOpen || !settingsPanelEl) return;
    if (settingsPanelEl.contains(event.target)) return;
    setSettingsOpen(false);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setSettingsOpen(false);
    }
  });

  if (!modelOptionsEl) return;
  modelOptionsEl.addEventListener("click", function (event) {
    const optionButton = event.target.closest(".settings-option[data-model]");
    if (!optionButton) return;

    const nextModel = optionButton.dataset.model;
    if (!isKnownModel(nextModel)) {
      return;
    }

    selectedModel = nextModel;
    writeStoredModel(selectedModel);
    populateModelOptions();
    setModelSelectEnabled(!requestInFlight);
    setSettingsOpen(false);
  });
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInlineMarkdown(text) {
  return text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/__([^_]+)__/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/_([^_]+)_/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer noopener">$1</a>');
}

function renderMarkdown(markdownText) {
  const source = String(markdownText || "").replace(/\r\n/g, "\n");
  const codeBlocks = [];

  const withCodePlaceholders = source.replace(/```([\w-]+)?\n([\s\S]*?)```/g, (_, language, code) => {
    const token = `@@CODE_BLOCK_${codeBlocks.length}@@`;
    const languageLabel = language ? `<div class="code-lang">${escapeHtml(language)}</div>` : "";
    codeBlocks.push(`<pre class="code-block">${languageLabel}<code>${escapeHtml(code.trimEnd())}</code></pre>`);
    return token;
  });

  const lines = withCodePlaceholders.split("\n");
  const chunks = [];
  let paragraphLines = [];
  let listType = null;
  let listItems = [];
  let quoteLines = [];

  function flushParagraph() {
    if (!paragraphLines.length) return;
    const paragraph = renderInlineMarkdown(escapeHtml(paragraphLines.join("<br>")));
    chunks.push(`<p>${paragraph}</p>`);
    paragraphLines = [];
  }

  function flushList() {
    if (!listItems.length) return;
    const tag = listType === "ol" ? "ol" : "ul";
    chunks.push(`<${tag}>${listItems.map((item) => `<li>${item}</li>`).join("")}</${tag}>`);
    listType = null;
    listItems = [];
  }

  function flushQuote() {
    if (!quoteLines.length) return;
    const content = renderInlineMarkdown(escapeHtml(quoteLines.join("<br>")));
    chunks.push(`<blockquote>${content}</blockquote>`);
    quoteLines = [];
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();

    if (!trimmed) {
      flushParagraph();
      flushList();
      flushQuote();
      continue;
    }

    if (/^@@CODE_BLOCK_\d+@@$/.test(trimmed)) {
      flushParagraph();
      flushList();
      flushQuote();
      chunks.push(trimmed);
      continue;
    }

    const heading = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flushParagraph();
      flushList();
      flushQuote();
      const level = heading[1].length;
      chunks.push(`<h${level}>${renderInlineMarkdown(escapeHtml(heading[2]))}</h${level}>`);
      continue;
    }

    const quote = trimmed.match(/^>\s?(.*)$/);
    if (quote) {
      flushParagraph();
      flushList();
      quoteLines.push(quote[1]);
      continue;
    }

    const unordered = trimmed.match(/^[-*+]\s+(.*)$/);
    if (unordered) {
      flushParagraph();
      flushQuote();
      if (listType && listType !== "ul") {
        flushList();
      }
      listType = "ul";
      listItems.push(renderInlineMarkdown(escapeHtml(unordered[1])));
      continue;
    }

    const ordered = trimmed.match(/^\d+\.\s+(.*)$/);
    if (ordered) {
      flushParagraph();
      flushQuote();
      if (listType && listType !== "ol") {
        flushList();
      }
      listType = "ol";
      listItems.push(renderInlineMarkdown(escapeHtml(ordered[1])));
      continue;
    }

    flushList();
    flushQuote();
    paragraphLines.push(trimmed);
  }

  flushParagraph();
  flushList();
  flushQuote();

  let rendered = chunks.join("");
  codeBlocks.forEach((codeBlock, index) => {
    rendered = rendered.replace(`@@CODE_BLOCK_${index}@@`, codeBlock);
  });
  return rendered;
}

function getBubbleContentEl(bubble) {
  return bubble.querySelector(".message-content") || bubble;
}

function setBubbleText(bubble, text) {
  getBubbleContentEl(bubble).textContent = text || "";
}

function setBubbleMarkdown(bubble, text) {
  getBubbleContentEl(bubble).innerHTML = renderMarkdown(text || "");
}

function syncViewportMetrics() {
  const viewportHeight = Math.max(window.innerHeight || 0, document.documentElement.clientHeight || 0, 640);
  const chatGap = Math.max(12, Math.round(viewportHeight * 0.02));

  document.documentElement.style.setProperty("--page-height", `${viewportHeight}px`);
  document.documentElement.style.setProperty("--chat-page-gap", `${chatGap}px`);
}

function syncFrameHeight() {
  try {
    const frame = window.frameElement;
    if (!frame || !window.parent || !window.parent.document) {
      return;
    }

    const parentViewportHeight = window.parent.innerHeight || window.parent.document.documentElement.clientHeight;
    const frameTop = frame.getBoundingClientRect().top;
    const nextHeight = Math.max(640, Math.floor(parentViewportHeight - frameTop - 6));

    if (nextHeight > 0) {
      frame.style.height = `${nextHeight}px`;
    }
  } catch (error) {
    // Ignore sandbox or cross-frame access issues and keep the fallback height.
  }
}

function streamTitle() {
  if (!heroTextEl) return;
  if (titleIndex <= fullTitle.length) {
    heroTextEl.textContent = fullTitle.slice(0, titleIndex);
    titleIndex += 1;
    const nextDelay = 30 + Math.floor(Math.random() * 55);
    setTimeout(streamTitle, nextDelay);
  }
}

function ensureChatShell() {
  if (!chatShellEl || chatShellEl.dataset.initialized === "true") return;
  chatShellEl.innerHTML = '<div class="chat-thread" id="chat-thread"><div class="chat-empty" id="chat-empty">在这里开始对话</div></div>';
  chatShellEl.dataset.initialized = "true";
}

function getChatThread() {
  ensureChatShell();
  return document.getElementById("chat-thread");
}

function clearEmptyState() {
  const emptyEl = document.getElementById("chat-empty");
  if (emptyEl) emptyEl.remove();
}

function scrollChatToBottom() {
  const thread = getChatThread();
  if (!thread) return;
  thread.scrollTop = thread.scrollHeight;
}

function appendMessage(role, text, options = {}) {
  clearEmptyState();
  const thread = getChatThread();
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  if (options.waiting) {
    bubble.classList.add("waiting");
  }

  const content = document.createElement("div");
  content.className = "message-content";
  bubble.appendChild(content);

  if (options.markdown) {
    setBubbleMarkdown(bubble, text || "");
  } else {
    setBubbleText(bubble, text || "");
  }

  row.appendChild(bubble);
  thread.appendChild(row);
  scrollChatToBottom();
  return bubble;
}

function appendMetrics(bubble, metrics) {
  if (!bubble || !metrics) return;
  const meta = document.createElement("div");
  meta.className = "message-meta";
  const latency = metrics.latency_seconds != null ? `${metrics.latency_seconds.toFixed(3)}s` : "N/A";
  const firstToken = metrics.first_token_latency_seconds != null ? `${metrics.first_token_latency_seconds.toFixed(3)}s` : "N/A";
  meta.textContent = `模型: ${metrics.model || "N/A"} | 首 token: ${firstToken} | 总耗时: ${latency}`;
  bubble.appendChild(meta);
}

function setComposerEnabled(enabled) {
  inputEl.disabled = !enabled;
  sendBtn.disabled = !enabled;
  setModelSelectEnabled(enabled);
}

async function streamChat(userText, model) {
  if (!streamApiUrl) {
    throw new Error("streamApiUrl is not configured");
  }

  const response = await fetch(streamApiUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_input: userText,
      smooth: true,
      model: model || undefined,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let assistantBubble = appendMessage("assistant", "正在等待响应...", { waiting: true });
  let assistantText = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) continue;
      const event = JSON.parse(line);

      if (event.type === "pulse") {
        if (event.stage === "accepted") {
          setBubbleText(assistantBubble, "正在连接模型...");
          assistantBubble.classList.add("waiting");
        }
        if (event.stage === "first_token") {
          assistantText = "";
          setBubbleMarkdown(assistantBubble, "");
          assistantBubble.classList.remove("waiting");
        }
      }

      if (event.type === "delta") {
        assistantBubble.classList.remove("waiting");
        assistantText += event.content || "";
        setBubbleMarkdown(assistantBubble, assistantText);
        scrollChatToBottom();
      }

      if (event.type === "done") {
        assistantBubble.classList.remove("waiting");
        assistantText = event.content || assistantText;
        setBubbleMarkdown(assistantBubble, assistantText);
        appendMetrics(assistantBubble, event.metrics);
        scrollChatToBottom();
      }

      if (event.type === "error") {
        assistantBubble.classList.remove("waiting");
        setBubbleText(assistantBubble, `请求失败：${event.message || "unknown error"}`);
      }
    }
  }
}

function enterChatMode() {
  if (hasEnteredChatMode || !pageEl) return;
  hasEnteredChatMode = true;
  ensureChatShell();
  pageEl.classList.add("chat-mode");
}

async function handleSubmit() {
  if (requestInFlight) return;
  const text = inputEl.value.trim();
  if (text) {
    const requestModel = isKnownModel(selectedModel) ? selectedModel : getFallbackModel();
    enterChatMode();
    setSettingsOpen(false);
    appendMessage("user", text);
    inputEl.value = "";
    requestInFlight = true;
    setComposerEnabled(false);

    try {
      await streamChat(text, requestModel);
    } catch (error) {
      appendMessage("assistant", `请求失败：${error.message || error}`);
    } finally {
      requestInFlight = false;
      setComposerEnabled(true);
    }
  }
  inputEl.focus();
}

sendBtn.addEventListener("click", handleSubmit);
inputEl.addEventListener("keydown", function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
});

function startHeroAnimation() {
  if (heroTitleEl && heroTitleEl.parentElement) {
    heroTitleEl.parentElement.classList.add("ready");
  }
  streamTitle();
  syncViewportMetrics();
  syncFrameHeight();
}

window.addEventListener("fullscreenchange", syncViewportMetrics);
window.addEventListener("resize", syncFrameHeight);
window.addEventListener("resize", syncViewportMetrics);
window.addEventListener("load", syncFrameHeight);
window.addEventListener("load", syncViewportMetrics);
setTimeout(syncViewportMetrics, 0);
setTimeout(syncViewportMetrics, 120);
setTimeout(syncViewportMetrics, 360);
setTimeout(syncFrameHeight, 0);
setTimeout(syncFrameHeight, 120);
setTimeout(syncFrameHeight, 360);

if (document.fonts && document.fonts.ready) {
  document.fonts.ready.then(() => requestAnimationFrame(startHeroAnimation));
} else {
  requestAnimationFrame(startHeroAnimation);
}

initializeModelSettings();
inputEl.focus();
