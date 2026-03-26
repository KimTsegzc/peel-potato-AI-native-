**This is a human write file './architect.md' to make things controllable.**
**AI agents should read to understand.**
**No AI should/could/would make any change.**

<!-- STATEMENT -->
# This is md file that claims ways of building whole project.
# a vission and scope statement is at ./readme.md.

<!-- FRONTEND -->
# Frontend Architect
## main and only page
Let's make this a chatbot-like UI. an './Gateway/Front/app.py' would make it.

## style and reference
- **farmework:** Streamlit
- **Style:** Conversational UI/UX
- **UI Reference:** 
    - [ChatGPT](https://chatgpt.com/)
    - there is a wanted page look at './Gateway/Front/page_referencee.png'
    - the avatar pic is at './Gateway/Front/xiexin-avatar.png'

## Openup
'我是鑫哥，帮你搞搞数据' would be on the page, with an avatar.
line would 'streaming' out like a talktive greeting.
a 'ask anything' bar like [ChatGPT] would be under it.
that's it, simple and easy.

<!-- INTERACTIVES -->
## Interactive
**This is important! it gives event connected Front-end and Back-end.**
- [send]a send button(clickable), by default shortcut 'enter'. it wraps up the input with prefix 'user: ', then send it to ./orchestrator.py for a ask.


<!-- BACKEND -->
# Backend Architect
## We use an agentic way of working:
- **./orchestrator.py:** Do the 'Brain' work.
    1. it receives info from different components, and let the logic runs through.
    2. it's also human write only, no LLM hallucination would affect the main logic.
- **./Gateway/Back:** provides funtion to call.
    1. LLM-provider.py with a LLM-provider-function.md.