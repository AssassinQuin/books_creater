---
name: story-flow
description: 网文创作总入口（ZCode 工作区层，自持体系）— 意图路由到 novel-* 五技能主干（达尔文版），调度子 agent，协同 MCP 与 hook 守卫；对标拆书/调研/上架等周边流程本 skill 自持。触发：/story-flow、「小说流程」「流水线」及 novel-* 触发词未明确路由时。
---

# story-flow：ZCode 网文创作总入口（自持体系）

> 承接达尔文版 novel-writer 总路由职责。**全流程只用本工作区自持资源**（novel-* 五技能 + .zcode/knowledge 知识库 + story-flow MCP + hooks），不依赖任何外部 skill 体系。

## 意图路由

```
关键词                                    → 调用 Skill（主力 agent）
────────────────────────────────────────────────────────────
"头脑风暴"/"灵感"/"我有个想法"/"开书"      → novel-setup（setup-architect）
"建世界观"/"世界观"/"设定"                 → novel-setup A2（setup-architect）
"设计人物"/"加人物"/"人物卡"/"人物采访"     → novel-character（character-smith）
"规划卷"/"大纲"/"出细纲"/"补细纲"          → novel-planner（plot-planner）
"写第N章"/"继续写"/"写一章"/"日更"/"续写"  → novel-chapter-writer（chapter-writer）
"审阅"/"检查"/"诊断"/"卡文"/"写不动"       → novel-doctor（novel-doctor）
"改设定"/"改人物"/"调整"                   → novel-doctor C3 级联更新（最高优先级）
"上架"/"发布"/"番茄"/"起点"                → C1 本 skill 自持
"进度"/"状态"                             → D1 本 skill 处理
"搜一下{关键词}"                           → D2 本 skill 处理
"拆书"/"对标采集"/"分析小说"               → E1 对标拆书（本 skill 自持）
"调研"/"查资料"/"深度调研"                 → E2 调研（web-research 用户级 skill）
无匹配 → book_status 查进度，建议下一步
```

### 冲突消歧优先级（从高到低）

1. **C3 级联更新**（"改设定"/"改人物"）→ novel-doctor — 立即处理，防止脏数据扩散
2. **B2 写作中断**（写作中说"改设定"）→ 暂停写作，先走 novel-doctor 再回来
3. **A 层重建** → 按用户意图路由，不强制顺序
4. **模糊匹配** → "帮我写"无上下文时 `book_list` 问用户操作哪个项目

## 资源地图（全部自持）

| 资源 | 位置 |
|---|---|
| 五技能主干 | `.zcode/skills/novel-{setup,character,planner,chapter-writer,doctor}/` |
| 子 agent 简报 | `.zcode/agents/`：setup-architect / character-smith / plot-planner / chapter-writer / novel-doctor |
| MCP 工具 | `mcp__story-flow__*`（13 个，见下表） |
| 方法论库 | `.zcode/knowledge/craft/`（75 文件现役收编，含 37 题材文笔卡） |
| 历史知识库 | `.zcode/knowledge/legacy/`（达尔文版：蒸馏法/场景指南/语料风格/头脑风暴话术） |
| 调研成果 | `参考资料/`（含 网文写手写作逻辑/ 深度调研） |
| 蒸馏借鉴库 | `素材库/借鉴库/`（12 作品 588 md） |
| 拆文库 | `拆文库/`（对标拆书产出） |
| 内置脚本 | `.zcode/mcp/story-flow/scripts/`（tracking_commit.py + 4 检测脚本） |
| 书目 | `novels/{书名}/` |

## 子 agent 启动协议

ZCode 以 `general-purpose` 子 agent + 简报文件实现自定义 agent：

```
Agent(subagent_type="general-purpose") 的 prompt =
  """先 Read 仓库根下 .zcode/agents/{agent名}.md —— 你的完整角色简报，按其必读表实际读取参考后执行。
  任务参数：
  - 书目：novels/{书名}
  - 任务类型/范围：{来自对应 skill 的阶段定义}
  - 素材/数据包：{召回的设定摘要 或 prose_pack 全文 或 审阅数据包}
  - 参考清单：{ref_route 返回的必读文件列表，带 why}
  - 产出路径：{约定文件}"""
```

要点：任务提示**自包含**（子 agent 看不到本对话）；创作类任务 spawn 前先 `ref_route`；子 agent 回报「已读参考/产出/未尽」三件套。

## MCP 工具速查（mcp__story-flow__*）

| 工具 | 用途 | 谁在用 |
|---|---|---|
| `book_list` / `book_use` / `book_status` | 书目清单/切换/仪表盘 | 本 skill D1、各 skill 断点续传 |
| `outline_next` | 下一章细纲 | novel-chapter-writer Step 1 |
| `context_pack(chapter)` | 轻量上下文 | novel-doctor 数据获取、恢复上下文 |
| `ref_route(topic)` | 主题→权威文件路由（16 主题） | **每次 spawn 创作类 agent 前** |
| `ref_search(query, scope)` | 跨库全文检索（craft/borrow/market/research/book） | D2 全局搜索、级联分析、借鉴检索 |
| `prose_pack(chapter)` | 写前强制打包+记账+细纲三要素质检 | novel-chapter-writer Step 2（**每章必调**） |
| `checkout_status(chapter)` | 查账本 | 诊断 hook 拦截 |
| `tracking_init/commit/check` | 追踪事务（内置脚本） | novel-planner 首批细纲后 / novel-chapter-writer Step 10 / doctor |
| `ai_check(target)` | AI 味+退化检测（内置脚本） | novel-chapter-writer Step 9、doctor B线 |

## Hook 守卫（已自动生效）

| 事件 | 行为 |
|---|---|
| SessionStart | 注入当前书目+状态卡路径+连续性检查 |
| UserPromptSubmit | 写作意图消息自动附书目进度 |
| PreToolUse | **deny**：无细纲 / 无追踪状态 / 无 prose_pack 账本的正文写入（拆文库导书窗口豁免） |
| PostToolUse | 正文落盘检查 + AI 味 blocking 指纹清单 |

被拦截 → 按提示修复（补细纲 / prose_pack / tracking init），不绕过。

## C1: 平台上架（自持）

触发: "上架"/"发布"
1. `ref_route(平台上架)` 取平台规则（legacy platform-rules.md）
2. `book_status` + 设定召回
3. 合规检查 + 降 AI 率（novel-chapter-writer 步骤 8-9 的毒句式/禁词流程 + `ai_check` 全书抽检）+ 排版适配
4. 输出 `novels/{书名}/上架版/`

## D: 查询

**D1 状态总览**（"进度"/"状态"）：`book_status` → 项目/阶段/章数/字数/伏笔/下一章细纲状态
**D2 全局搜索**（"搜一下"）：`ref_search(keyword, scope="all")`

## E1: 对标拆书（自持采集流程）

触发: "拆书"/"分析小说"/建立对标。产出供 prose_pack 消费的权威模块。

1. 用户提供文本（文件路径或粘贴）+ 指定对标角色（主对标/副对标）
2. spawn general-purpose agent，任务提示注入：`.zcode/knowledge/legacy/novel-writer/references/book-analysis-guide.md`（拆书方法）+ 肘子段落拆解法（看到好段落反复琢磨内在逻辑，萃取模式不抄内容）
3. 产出结构（`拆文库/{书名}/`，绑定书目时复制子集到 `novels/{书名}/对标/{书名}/`）：
   - `剧情/情绪模块.md`（**权威**：读者需求/情绪引擎/可复现模块）与 `剧情/节奏.md`（**权威**：关键信息推进/情绪触动点/爆发节奏）——prose_pack 的硬依赖
   - `文风.md`（句长/标点/对话潜台词/锚点片段）
   - `章节/第N章_摘要.md`（含 `基调：X` 行，供对标匹配章挑选）
   - 角色/剧情/设定结构化子集
4. 借鉴模式（不拆全书时）：`ref_search(模式关键词, scope="borrow")` 从 素材库/借鉴库/ 587 文件蒸馏库取用——借模式不抄表达
5. `git commit -m "对标: {书名} 拆解入库"`

## E2: 调研（外部知识）

触发: "调研"/"查资料"。走用户级 `web-research` skill（非小说体系，通用调研编排），成果按惯例存 `参考资料/{主题}/`。调研报告可通过 `ref_route(作者思维与写作逻辑)` 被流水线消费。

## Compact 后恢复

1. `book_status` 看进度 → 2. 读 `追踪/上下文.md`（存在则整份） → 3. `context_pack(下一章)` → 4. 回到 novel-chapter-writer Step 1

## 硬性规则

1. **先参考后创作**：spawn 创作类 agent 前必须 `ref_route`；写正文前必须 `prose_pack`（缺三要素/权威模块按 gaps 提示先修）
2. **流程纪律**（达尔文版继承 + 调研结论）：🔒检查点不可跳；角色蒸馏4步缺一不可；正文写完立即 tracking_commit；审阅必须落盘报告；**两短一长期待不断链**；**爽点章尾必接新期待**
3. **正文批量上限**：单轮≤3章；日更默认2-3章；超出拆轮
4. **方法论冲突时**：主题材文笔卡（项目内 > craft 索引匹配）> 对标情绪模块/节奏 > craft 通用方法论 > 借鉴库模式
