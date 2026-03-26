**This is a human write file './readme.md' to make things controllable.**
**AI agents should read to understand.**
**No AI should/could/would make any change.**

<!-- STATEMENT -->
# project statement
## This is an AI native or say AI ready project.
## Readme is a charter of this project.
## some detailed defines the way of building loads in ./architect.md.

<!-- INFO -->
# project info
- **Author:**   XIE Xin
- **Name:**     XIEXin_da_agent
- **Design and Devloped in:** Guangzhou
- *Version:*    2.3

<!-- SCOPE -->
# Project Scope 
## an Agent that helps Data analysist to work seamlessly. in a agentic way:
## There are skill set to provide skills, and the main ./orchestrator.py would be central dispatcher.
1. skill-res:       Recognize and resolve the data.
2. skill-peel:      Deal with columns and rows.
3. skill-pretty:    Prettify the table with embeded formats.
4. skill-viz:       Provides Visuallization toolkits.
5. skill-stat:      Offers basic statistical methods to descriptive/predictive analysis.
6. skill-comm:      LLM-based Comments on data comprehension.
7. skill-advs:      LLM-based advice to do work, WorkingEnviroments/Goals/Rules/KnowledgeBase needed.

<!-- Directories -->
# Directories
It has:
1. **Memo:** contains ./Memo/metadata, some metadata like Dict.json a mapping for columns to select and rename. and other groups xlsx may be packed up here.
2. **Skills:** ./Skills/sudo-name-skill kebab-case named skill folders, with a .md file to anounce it which has name same as skill(constraint with JSON Schema for input and output),  a scripts, an input and a output foder inside.
3. **Gateway:** has ./Gateway/LLM provides LLM service. ./Gateway/Front as UI page.
4. **orchestrator.py** main controlling process, **Human built, AI can read but never make any change**.
5. **Launcher:** support Go_XIEXin.exe as a Launcher.