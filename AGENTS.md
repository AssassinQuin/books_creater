# books_creater — 网文写作项目（ZCode 工作区指令）

本仓库创作主干 = **novel-* 五技能**（达尔文版，`.zcode/skills/novel-setup/character/planner/chapter-writer/doctor`），总入口 `/story-flow`（`.zcode/skills/story-flow/`）。**全流程自持**：知识库、脚本、agent 均在 `.zcode/` 下，不依赖外部 skill 体系。完整路由见 story-flow SKILL.md。

## 核心约束（每次会话生效）

1. **先参考，后创作**：设定/大纲/正文生成前，先用 `mcp__story-flow__ref_route` / `prose_pack` 把权威材料装进上下文。知识库：`.zcode/knowledge/craft/`（现役方法论 75 文件+37 题材文笔卡）、`.zcode/knowledge/legacy/`（达尔文版深度指南）、`素材库/借鉴库/`（12 作品蒸馏）、`参考资料/`（调研成果，含网文写手写作逻辑）。
2. **写正文章节硬顺序**（novel-chapter-writer）：细纲（含三要素：目标/阻碍/爆点）→ `prose_pack(chapter)` → spawn chapter-writer 写入 → `ai_check` 清零 blocking → `tracking_commit`。hooks（`.zcode/config.json`）机械拦截违规写入，被拦按提示修复，不要绕过。
3. **流程纪律**：🔒检查点不可跳；角色蒸馏4步缺一不可；正文写完立即 tracking_commit；审阅必须落盘 `审阅报告/`；**两短一长期待不断链，爽点章尾必接新期待**（满足性弃书是追读第一杀手）；每500字一个甜头。
4. **AI 对抗性指令**：留白优先（藏角色心思/潜台词/不点破情绪）——AI 天生消除歧义，需刻意保留信息缺口。
5. **结构化状态唯一通道**：`mcp__story-flow__tracking_init / tracking_commit`（透传内置 `tracking_commit.py`）。禁止手改 `追踪/_tracking-state.json` 及派生视图。
6. 书目在 `novels/{书名}/`；活跃书目 = `.active-book`。共享资料：`拆文库/`、`素材库/`、`参考资料/`。
7. 用户并行手改文件时（尤其正文/设定），回写前必须重读合并，禁止盲盖。

## 工具链（全部自持于 .zcode/）

- **子 agent**（5 个，由各 skill 以 general-purpose spawn）：setup-architect、character-smith、plot-planner、chapter-writer、novel-doctor
- **MCP** `story-flow`（13 工具）：书目/细纲/上下文打包/参考路由检索（16主题）/prose_pack 账本+三要素质检/追踪事务/AI 味检测
- **Hooks**：SessionStart 状态注入；UserPromptSubmit 进度提示；PreToolUse 三重门禁（细纲→追踪→账本）；PostToolUse 落盘+AI 味检测
- **脚本**：`.zcode/mcp/story-flow/scripts/`（tracking_commit.py、check-ai-patterns/degeneration/outline-copy、normalize-punctuation）
- Compact 后恢复：`book_status` → 读 `追踪/上下文.md` → `context_pack(下一章)`
