from pathlib import Path
import base64

import streamlit as st
import streamlit.components.v1 as components

avatar_path = Path(__file__).parent / "xiexin-avatar.png"

st.set_page_config(
    page_title="xiexin-da-agent",
    page_icon=str(avatar_path),
    layout="wide",
)

hide_decoration_bar_style = """
<style>
  header {visibility: hidden;}
  [data-testid="stDecoration"] {display: none;}
</style>
"""
st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)

with open(avatar_path, "rb") as img_file:
    avatar_b64 = base64.b64encode(img_file.read()).decode("utf-8")

html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {{
    --text: #111827;
    --border: #e5e7eb;
    --bg: #ffffff;
  }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    background: #ffffff;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  }}

  .page {{
    min-height: 100vh;
    display: flex;
    justify-content: flex-start;
    align-items: center;
    flex-direction: column;
    padding-top: 90px;
  }}

  .content {{
    width: min(900px, 92vw);
    margin: 0 auto;
  }}

  .hero {{
    display: flex;
    align-items: center;
    gap: 22px;
    width: fit-content;
    margin: 0 auto;
  }}

  .hero-avatar {{
    width: 104px;
    height: 104px;
    border-radius: 50%;
    object-fit: cover;
    flex: 0 0 auto;
  }}

  .hero-title {{
    margin: 0;
    color: var(--text);
    font-size: 38px;
    line-height: 1.2;
    font-weight: 700;
  }}

  .input-wrap {{
    margin-top: 46px;
    width: 82%;
    margin-left: auto;
    margin-right: auto;
  }}

  .input-box {{
    width: 100%;
    height: 74px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--bg);
    padding: 0 16px 0 34px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }}

  .input-box:focus-within {{
    border-color: #3b82f6;
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.15);
  }}

  .input-box input {{
    flex: 1;
    border: 0;
    outline: 0;
    background: transparent;
    color: var(--text);
    font-size: 18px;
    line-height: 1.2;
    padding: 0 6px 0 0;
    font-family: inherit;
  }}

  .input-box input::placeholder {{
    color: #d1d5db;
  }}

  .send-btn {{
    width: 42px;
    height: 42px;
    border: 0;
    border-radius: 50%;
    background: #000000;
    color: #ffffff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex: 0 0 auto;
    font-size: 20px;
    padding: 0;
  }}

  .send-btn:active {{
    transform: scale(0.96);
  }}

  @media (max-width: 900px) {{
    .page {{ padding-top: 48px; }}
    .hero-avatar {{ width: 76px; height: 76px; }}
    .hero-title {{ font-size: 32px; }}
    .input-box {{ height: 64px; }}
    .input-wrap {{ width: 92%; }}
    .input-box {{ padding: 0 14px 0 24px; }}
    .input-box input {{ font-size: 20px; }}
  }}
</style>
</head>
<body>
  <div class="page">
    <div class="content">
      <div class="hero">
        <img class="hero-avatar" src="data:image/png;base64,{avatar_b64}" alt="avatar" />
        <h1 class="hero-title">我是鑫哥，帮你搞搞数据</h1>
      </div>

      <div class="input-wrap">
        <div class="input-box">
          <input id="chat-input" type="text" placeholder="Ask anything" autocomplete="off" />
          <button id="send-btn" class="send-btn">➤</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    const inputEl = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");

    function handleSubmit() {{
      const text = inputEl.value.trim();
      if (text) {{
        console.log("Chat input:", text);
        inputEl.value = "";
      }}
      inputEl.focus();
    }}

    sendBtn.addEventListener("click", handleSubmit);
    inputEl.addEventListener("keydown", function (e) {{
      if (e.key === "Enter" && !e.shiftKey) {{
        e.preventDefault();
        handleSubmit();
      }}
    }});

    inputEl.focus();
  </script>
</body>
</html>
"""

components.html(html, height=430, scrolling=False)
