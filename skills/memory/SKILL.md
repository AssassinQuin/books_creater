---
name: memory
description: >
  ⚠️ MANDATORY GATE: This skill MUST be loaded BEFORE any memory_memory_* tool is called.
  If the user's intent involves storing, retrieving, searching, or managing persistent memories,
  load this skill first — do NOT call memory MCP tools directly.
  
  Persistent memory management across sessions. Triggers on ANY of these patterns:
  
  Explicit: "remember this", "recall", "load memory", "save to memory", "show my memories",
  "extract learnings", "记忆", "记住", "保存", "回忆", "加载记忆", "保存记忆",
  "提取记忆", "项目记忆", "全局记忆", "记忆管理", "展示记忆", "看看记忆".
  
  Implicit: user states a fact/preference/decision they want persisted for future sessions,
  user asks "what did we decide before", user says "之前怎么做的", any request to
  persist context across sessions. Also triggers when other skills need to store or
  retrieve memories — always route through this skill for proper tag compliance.
  
  Chinese bare verbs that MUST trigger: "记忆", "记住", "存一下", "记一下", "别忘了".
allowed-tools:
  - memory_memory_store
  - memory_memory_store_session
  - memory_memory_search
  - memory_memory_list
  - memory_memory_delete
  - memory_memory_cleanup
  - memory_memory_health
  - memory_memory_stats
  - memory_memory_update
  - memory_memory_ingest
  - memory_memory_harvest
  - memory_memory_quality
  - memory_memory_graph
  - memory_memory_conflicts
  - memory_memory_resolve
  - Read
  - Bash
  - Glob
  - Grep
---

# Memory Skill

Persistent knowledge management across AI coding sessions.

**工具参数完整参考**：[references/mcp-tools.md](references/mcp-tools.md) — 所有 16 个 MCP 工具的参数签名。
**安装与运维**：[references/installation.md](references/installation.md) — MCP server 安装、版本、配置、数据位置。

## ⚠️ 强制守门

**此 skill 是所有 memory MCP 工具调用的唯一合法入口。**

orchestrator 在以下情况**必须先加载本 skill**，禁止直接调用 `memory_memory_*` 工具：
1. 用户请求涉及「记忆/记住/存储/回忆/加载记忆」等意图
2. 其他 skill 需要存储或检索记忆（应委托本 skill 执行）
3. 会话结束时的 `memory_harvest` 操作

**违反后果**：直接调用 `memory_store` 会缺失 scope+type 双标签，导致记忆无法被正确过滤和检索，污染知识库。

验证方式：skill 加载后，Phase 0 (Health Check) 是第一个动作。如果跳过 Phase 0 直接调用工具，说明守门失败。

## 触发路由

```
用户请求 → Phase 0 (Health) 前置检查
  ├─ "回忆/之前做了什么/项目上下文"       → Phase 1
  ├─ "展示记忆/管理记忆/看看记忆"         → Phase 2
  ├─ "加载记忆/注入记忆/加载项目记忆"     → Phase 3
  ├─ "记住这个/保存决策" (单条)           → Phase 4A
  ├─ "保存记忆/提取记忆/结束会话" (批量)   → Phase 5
  ├─ "记忆健康/清理记忆"                 → Phase 6
  ├─ 裸动词触发                          → Phase 4A
  │   "记忆 X" / "记住 X" / "存一下" / "记一下" / "别忘了"
  ├─ 隐式存储意图                        → Phase 4A
  │   用户陈述事实+偏好+决策 且暗示要持久化
  │   判定："以后都用X" / "这个要记住" / "以后别忘"
  ├─ 跨 skill 委托                       → Phase 4A
  │   其他 skill 需存储/检索记忆时，传入三元组:
  │   {content: str, scope: project:<name>|shared|global, type: decision|convention|...}
  └─ 无明确意图                          → Phase 1 展示摘要
```

## 标签体系 v2

### Scope（必填其一）

| Scope | 格式 | 含义 | 示例 |
|-------|------|------|------|
| **项目专属** | `project:<name>` | 仅 `<name>` 项目可用，`<name>` = workspace root basename | `project:hs_analysis` |
| **共享** | `shared` | 跨项目复用的技术知识，不绑定特定项目 | Python async 模式、SQLite WAL 配置 |
| **全局** | `global` | 用户级偏好/工具配置，适用所有项目 | SSH clone、HTTP timeout 30s |
| **会话** | `session` | 临时会话状态，不持久复用 | 待办、中间状态 |

### Type（必填其一）

| Type | 含义 |
|------|------|
| `decision` | 架构/技术选型决策 |
| `convention` | 编码规范、命名规则 |
| `preference` | 用户偏好 |
| `learning` | 经验教训、洞察 |
| `context` | 项目状态、事实信息 |
| `bug` | 已知问题及修复 |
| `reference` | 文档参考 |
| `pattern` | 可复用的代码模式/解决方案配方 |

### Lifecycle（可选，metadata.lifecycle）

| 阶段 | 质量 | 含义 | 晋升条件 |
|------|------|------|---------|
| `raw` | 默认 0.5 | 刚创建，未经审查 | 初始状态 |
| `refined` | ≥0.7 | 已审查精炼，内容准确 | 人工 rate +1 或自动压缩后 |
| `canonical` | ≥0.9 | 多次验证，高质量权威记忆 | refined + 被检索≥3次 + 无冲突 |
| `archived` | — | 已过时/被替代 | 主动归档 |

### 存储格式

```
tags: ["<scope>", "<type>"]          # 双标签，缺一拒绝
metadata: { "lifecycle": "raw" }     # 可选，默认 raw
```

### 三级隔离原则

```
项目专属 (project:<name>)  — 只对该项目可见，强隔离
       ↕ 可检索
共享 (shared)              — 跨项目通用技术知识，任何项目可搜索到
       ↕ 可检索  
全局 (global)              — 用户偏好/工具配置，不含技术细节
```

**隔离规则**：
- `project:<name>` 严格隔离：`tags=["project:hs_analysis"]` 只返回该项目记忆
- `shared` 天然跨项目：`tags=["shared"]` 所有项目都能搜到
- `global` 天然跨项目：`tags=["global"]` 所有项目都能搜到
- **禁止提升**：项目记忆不得因为"可能通用"而存为 shared/global

**Scope 判定示例**：
- ❌ "hs_analysis 用 @dataclass" → `shared`（含项目特定选择）
- ✅ "hs_analysis 用 @dataclass" → `project:hs_analysis`（项目专属决策）
- ✅ "Python dataclass vs Pydantic: dataclass 更快用于纯数据" → `shared`（通用技术知识）
- ✅ "HTTP 请求超时设为 30s" → `global`（用户工作流偏好）
- ❌ "HTTP 请求超时设为 30s" → `shared`（这是偏好，不是技术知识）

---

## Cross-Skill API

**其他 skill 集成 memory 的标准化接口。此接口是稳定的，memory 内部标签体系变更不影响调用方。**

任何 skill 需要读写记忆时，遵循以下最小契约。无需加载本 skill 的完整 Phase 流程，只需遵守标签体系和调用规范。

### Scope 别名（稳定接口）

**其他 skill 始终使用以下别名，不使用 memory 内部的 `project:<name>` 格式。Memory 负责在存储时自动解析。**

| 别名 | 含义 | 存储时 memory 自动追加 |
|------|------|----------------------|
| `project` | 当前项目专属 | + `project:<workspace_basename>` |
| `shared` | 跨项目共享技术知识 | — |
| `global` | 用户偏好/工具配置 | — |
| `session` | 临时会话状态 | — |

**解耦原理**：
- 其他 skill 写 `tags: "project,decision"` → 永远不变
- Memory skill 存储时自动追加 `project:hs_analysis` → 实现精确隔离
- Memory 内部改标签格式 → 只需改解析规则，其他 skill 无感知

### 接口契约

```yaml
# 其他 skill 在自身 SKILL.md 中声明对 memory 的依赖：
#
# 1. 检索记忆（读）
#    - 调用前：无需加载 memory skill，直接调用 MCP 工具
#    - 必须带 tags 过滤，禁止无标签检索（性能+噪音）
#    - 使用 scope 别名（project/shared/global/session）
#
# 2. 存储记忆（写）
#    - 必须构造 scope别名 + type 双标签
#    - 推荐先 memory_search 去重，相似度>0.85 则更新而非新建
#
# 3. 降级策略
#    - memory 工具不可用时，跳过记忆操作，不阻塞主流程
```

### 读 API（检索）

其他 skill 检索记忆时，直接调用 MCP 工具，使用以下标准模式：

```
# 项目专属记忆（最常用）
memory_search(tags=["project"], limit=50)

# 共享记忆（跨项目技术知识）
memory_search(tags=["shared"], limit=50)

# 全局记忆（用户偏好）
memory_search(tags=["global"], limit=50)

# 三级检索（推荐顺序）
# 1. 项目专属 → 2. 共享 → 3. 全局
memory_search(query="<主题>", tags=["project"], limit=30)
memory_search(query="<主题>", tags=["shared"], limit=20)
memory_search(query="<主题>", tags=["global"], limit=10)

# 语义检索（带 query）
memory_search(query="<具体内容>", tags=["project"], limit=10)
memory_search(query="<具体内容>", mode="hybrid", quality_boost=0.3, limit=10)

# 时间范围
memory_search(tags=["project"], time_expr="last week", limit=20)
```

**规范**：
- 必须带 `tags` 参数，至少指定 scope 别名
- limit 建议 ≤50，防止上下文溢出
- 优先检索 `project`，再检索 `shared`，最后 `global`
- 对检索结果做结构化摘要后使用，不输出原始 JSON

### 写 API（存储）

其他 skill 存储记忆时，使用 scope 别名构造标签：

```
memory_store(
  content="<精炼后的内容>",                    # ← 必须经过精炼（见下方规范）
  metadata={ tags: "<scope别名>,<type>" }     # 双标签，使用别名
)
```

**scope 别名 + type 取值**：见上方「Scope 别名」表。

**自动解析**：memory skill 在 Phase 4/5 存储时，自动将 `project` 解析为 `project:<workspace_basename>` 并追加到 tags。调用方无需关心。

### 🔒 内容精炼规范（存储前必执行）

**所有写入操作（Phase 4/5/Cross-Skill）存储前必须精炼内容。禁止存储原始对话片段。**

精炼三步：

```
1. 提取核心事实：去掉对话语气词、重复表述、上下文依赖
2. 准确表达：用精确术语替代模糊描述，确保脱离原对话仍可理解
3. 精简到最小：一句话能说清不用两句，合并关联信息

对比示例：
  ❌ "用户说以后每次都不要用 Pydantic 了，要用 dataclass 代替，因为性能更好"
  ✅ "项目规范：数据模型用 @dataclass，不用 Pydantic（性能优先）"

  ❌ "之前调试的时候发现 timeout 设成 30 秒比较好，不然会卡住"
  ✅ "HTTP 请求超时设为 30s，防止挂起"

  ❌ "用户决定选择 SQLite 而不是 PostgreSQL 作为这个项目的数据库"
  ✅ "技术栈：SQLite（非 PostgreSQL），轻量本地存储场景"
```

**精炼检查清单**（每条记忆存储前过检）：

| 检查项 | 通过标准 |
|--------|---------|
| 可独立理解 | 脱离原对话上下文仍完全清晰 |
| 无冗余 | 删除所有"用户说""之前""其实"等对话残留 |
| 准确切题 | 核心事实一个不少，无关细节一个不多 |
| 长度合理 | 单条 ≤120 字符（约 2 行），超过则拆分或进一步压缩 |

**不通过则拒绝存储，返回精炼后版本等确认。**

### 推荐模式：

```
# 存储前先去重
memory_search(query="<内容摘要>", limit=5)
# → 如果相似度>0.85，用 memory_update 更新而非新建
# → 否则 memory_store 新建
```

### 常用场景速查

| 场景 | scope别名 | type | 示例调用 |
|------|----------|------|---------|
| skill 保存研究结果 | `project` | reference | `tags: "project,reference"` |
| skill 记录项目决策 | `project` | decision | `tags: "project,decision"` |
| skill 记录项目规范 | `project` | convention | `tags: "project,convention"` |
| skill 保存通用技术知识 | `shared` | pattern | `tags: "shared,pattern"` |
| skill 保存通用经验教训 | `shared` | learning | `tags: "shared,learning"` |
| skill 记录用户偏好 | `global` | preference | `tags: "global,preference"` |
| skill 记录 bug | `project` | bug | `tags: "project,bug"` |
| skill 保存会话状态 | `session` | context | `tags: "session,context"` |

### Skill 声明模板

其他 skill 在自身 SKILL.md 中引用 memory 时，建议包含以下声明块：

```markdown
## Memory Integration

遵循 [memory skill Cross-Skill API](../memory/SKILL.md)（稳定接口）：
- 使用 scope 别名：project / shared / global / session
- 检索：memory_search + tags 过滤（至少指定 scope 别名）
- 存储：memory_store + scope别名,type 双标签
- 去重：存储前 memory_search 检查相似度
- 降级：memory 不可用时跳过，不阻塞主流程
- ⚠️ 不要使用 memory 内部标签格式（如 project:<name>），只使用别名
```

### 跨 Skill 委托（高级）

当 skill 需要更复杂的记忆操作（批量提取、冲突解决、质量分析等），应委托 memory skill 执行：

```
# 委托方式：在 skill 中声明"此处需要 memory skill 的 Phase X 能力"
# orchestrator 会加载 memory skill 并执行对应 Phase
#
# 常见委托场景：
# - 会话结束时批量提取 → 委托 Phase 5
# - 记忆清理/去重 → 委托 Phase 6
# - 加载完整项目记忆 → 委托 Phase 3
```

---

## Phase 0: Health Check

所有路径前置条件：`memory_health()` → unhealthy 则 `memory_cleanup()` → 重检 → 仍失败报告用户。

---

## Phase 1: Retrieve

按需选择调用（不必全跑）：

| 子操作 | query | tags | 其他 |
|--------|-------|------|------|
| 1A 项目记忆 | `"<项目名> 架构 决策 规范 踩坑"` | `["project:<项目名>"]` | limit=50 |
| 1B 共享记忆 | `"<主题> 技术知识 模式 方案"` | `["shared"]` | limit=30 |
| 1C 全局记忆 | `"用户偏好 工作流 工具配置"` | `["global"]` | limit=20 |
| 1D 近期记忆 | `"最近工作 会话上下文"` | — | time_expr="last week" |
| 1E 语义搜索 | `"<自然语言>"` | 按需 | mode="hybrid", quality_boost=0.3 |

**输出格式**：结构化摘要（条数 + tags 分布 + 前 3 条重点内容）。不输出原始 JSON。
**空结果**：提示"无 {scope} 记忆" → 建议存入首条或 Phase 5 从会话提取。

---

## Phase 2: Display & Manage

**展示格式**：表格，列: `# | Type | Content Summary | Quality | Date`，按 scope 分组。

**操作**（展示后提供）：

| 操作 | 工具 | 要点 |
|------|------|------|
| 删除 | `memory_delete` | 必须 `dry_run=true` 预览后再确认 |
| 改元数据 | `memory_update` | 只改 tags/metadata，不改内容 |
| 改内容 | 删旧+存新 | 保留原 tags |
| 去重 | `memory_cleanup` | 自动移除重复 |
| 质量分析 | `memory_quality(action="analyze")` | 全局质量分布 |
| 新增 | `memory_store` | 必须含 scope+type 双标签 |

---

## Phase 3: Load

### 三级检索策略

**项目判定**：`项目名 = workspace root 的 basename`

按优先级从高到低检索，每级独立搜索：

```
# 1. 项目专属记忆（必做）— tags 精确隔离
memory_search(
  query="<项目名> 架构 决策 规范 踩坑 配置",
  tags=["project:<项目名>"],
  limit=100,
  max_response_chars=50000
)

# 2. 共享记忆（必做）— 跨项目通用技术知识
memory_search(
  query="技术方案 模式 踩坑 最佳实践",
  tags=["shared"],
  limit=50
)

# 3. 全局记忆（必做）— 用户偏好/工具配置
memory_search(
  query="偏好 工作流 工具配置 约定",
  tags=["global"],
  limit=50
)
```

**隔离原理**：
- `tags=["project:hs_analysis"]` 只返回该项目专属记忆，精确隔离
- `tags=["shared"]` 返回所有项目可复用的技术知识
- `tags=["global"]` 返回用户偏好，天然跨项目
- 三级检索确保：项目信息不泄露 + 共享知识可达 + 偏好全局可用

**注入会话**（检索后执行）：
```
## 🧠 Loaded Memory Context (HIGHEST PRIORITY)
以下记忆来自持久存储，作为本会话所有决策的权威上下文。子 agent 必须接收此内容。
<loaded_memories>
[项目专属记忆 | 共享记忆 | 全局记忆]
</loaded_memories>
```

**子 agent 传递**：委托时将上述 `<loaded_memories>` 块原样注入子 agent prompt。

**压缩保留**：`compress` 时 memory 内容必须原样保留在摘要中，禁止精简或截断。

**加载验证**（注入后展示）：
```
✅ 项目记忆: N 条 | ✅ 共享记忆: N 条 | ✅ 全局记忆: N 条 | ✅ 子 agent 模板就绪
⚠️ 质量低于 0.5: [列出] → 建议清理或进化
```

---

## Phase 4: Persist

**🔒 存储前强制精炼**：所有内容必须经过「内容精炼规范」处理后再存储。

**🔒 Scope 别名自动解析**：存储时执行以下解析，确保双标签共存：

```
# 解析规则（Phase 4/5 所有存储操作执行）
if tags contains "project":
    resolved = f"project:{workspace_basename}"
    tags.append(resolved)   # 追加精确 scope，保留别名

# 结果示例：
#   输入 tags: ["project", "decision"]
#   存储 tags: ["project", "project:hs_analysis", "decision"]
#
#   输入 tags: ["shared", "pattern"]
#   存储 tags: ["shared", "pattern"]  （无需解析）
```

**为什么保留双标签**：
- `project` → 其他 skill 搜索时用 `tags=["project"]` 可找到
- `project:<name>` → memory skill Phase 3 精确隔离时用
- 双标签确保：外部稳定接口 + 内部精确隔离

| 场景 | 工具 | 参数要点 |
|------|------|---------|
| 会话中即时存 | `memory_store` | 先精炼内容 → 自动解析 scope → + `conversation_id` 允许同会话多条 |
| 会话结束批量提取 | `memory_harvest(sessions=1, types=[...], dry_run=false)` | |
| 整体保存 | `memory_store_session(turns=[...], tags="project,session")` | |
| 裸动词存储 | `memory_store` | 解析 "记忆 X" → **精炼内容** → 推断 scope+type → 自动解析 → **🔒必须先展示等用户确认** |
| 跨 skill 委托 | `memory_store` | 接收 {content, scope别名, type} → **精炼** → 自动解析 scope → 存储 |

### Phase 4A 裸动词推断规则

当用户使用裸动词（"记忆/记住/存一下/记一下"）时，按以下启发式推断 scope + type：

**Scope 推断**（使用别名，存储时自动追加 `project:<name>`）：

| 内容特征 | → Scope 别名 | 示例 |
|----------|---------|------|
| 包含项目路径/项目名/技术栈特定词 | `project` | "记忆 所有构建文件放在 /Users/ganjie/skills/" |
| 通用技术知识/模式/方案，不含项目特定信息 | `shared` | "记住 SQLite WAL 模式配置方法" |
| 包含"所有项目"/"以后都"/"每次都"，且是偏好/配置 | `global` | "记住 以后都用 SSH clone" |
| 不确定 | **默认 `project`**（安全降级，可手动提升为 shared/global） | "记一下 timeout 30s" |

**Type 推断**：

| 内容特征 | → Type | 示例 |
|----------|--------|------|
| "放在X"/"在X目录"/"配置在" | `context` | "构建文件放在 /Users/ganjie/skills/dockerfile" |
| "以后都用X"/"每次都"/"规范是" | `convention` | "以后都用 SSH URL" |
| "决定X"/"选X"/"用X代替Y" | `decision` | "决定用 pytest 而不是 unittest" |
| "我喜欢"/"偏好" | `preference` | "我喜欢用暗色主题" |
| 陈述事实/经验/教训 | `learning` | "原来 async 不等于并发" |
| 不确定 | **默认 `context`**（最安全的通用类型） | — |

**推断后确认流程**（🔒强制）：
```
用户原文 → 精炼内容 → 推断 scope+type → 展示表格 → 用户确认/修改 → memory_store
展示格式:
  📝 原文: {用户原始表述}
  ✨ 精炼: {精炼后内容}
  🏷️ Tags: {scope},{type}
  ❓ 确认存储？(确认/修改内容/修改 scope/修改 type/取消)
```

---

## Phase 5: Session → Memory

触发："save to memory", "保存记忆", "提取记忆", 或会话结束。

### 5A: 提取信号

| 信号词 | → Type |
|--------|--------|
| "用X" "决定" "选X" | decision |
| "总是" "规范是" "约定" | convention |
| "以后都用X" "每次都" "记住X" "规范是" | convention |
| "我喜欢" "用X代替" "偏好" | preference |
| "不工作因为" "根因是" | bug |
| "原来" "错了" "教训" | learning |
| "X放在Y" "X在Y目录" "配置在" | context |
| 文件路径、repo 结构、配置 | context |

### 5B: 分类 Scope

使用 **scope 别名**（`project` / `shared` / `global`），存储时 Phase 4 自动追加 `project:<name>`。

**判定流程**（每条记忆必须过此检查）：
```
1. 引用了特定项目名/目录/技术栈？
   → 是 → project（存储时自动变为 project + project:<name>）

2. 是通用技术知识（模式、方案、经验），不含项目特定信息？
   → 是 → shared

3. 是用户偏好/工具配置，适用于所有项目？
   → 是 → global

4. 去掉项目名后内容仍有意义且是技术知识？
   → 是 → shared
   → 否 → project（内容依赖项目上下文）
```

**对比示例**：
| 内容 | Scope | 理由 |
|------|-------|------|
| "hs_analysis 用 @dataclass" | `project:hs_analysis` | 项目专属决策 |
| "Python dataclass 比 Pydantic 快" | `shared` | 通用技术知识 |
| "HTTP timeout 30s" | `global` | 用户工作流偏好 |
| "SQLite WAL 模式提升并发读" | `shared` | 通用技术知识 |
| "skills 仓库用 symlink 分发" | `project:skills` | 项目专属架构 |

### 5C: 去重

`memory_search(query="<候选摘要>", mode="hybrid", limit=5)` → 相似度>0.85 标记重复。

### 5D: 展示确认

表格：`# | Type | Content | Tags`，按 🟢项目 / 🟡共享 / 🔵全局 分组。
**必须等用户确认**后才可存储。用户可选：全部/部分/修改/拒绝。

### 5E: 存储

确认后逐条 `memory_store`（每条必须先过「内容精炼规范」），输出 `✅ P1 stored: hash=abc123...`

---

## Phase 6: Advanced

| 操作 | 工具 | 关键参数 |
|------|------|----------|
| 导入文档 | `memory_ingest` | file_path, tags, chunk_size=1000 |
| 质量评分 | `memory_quality` | action: rate/get/analyze |
| 冲突检测 | `memory_conflicts` → `memory_resolve` | winner_hash, loser_hash |
| 关联图 | `memory_graph` | action: connected/path/subgraph |
| 会话提取 | `memory_harvest` | sessions, types, dry_run |
| 缓存统计 | `memory_stats` | — |

### 记忆进化机制

**三步循环：压缩 → 合并 → 提升**

#### 6A 压缩（Condense）

将冗长或重复的多条记忆压缩为一条精炼记忆：

```
触发条件：
  - 同主题记忆 ≥3 条
  - 单条记忆 >120 字符
  - memory_quality 质量分 <0.5

操作：
  1. memory_search 找到同主题记忆组
  2. 提取核心信息，合并为一条精炼版本（≤120字符）
  3. memory_store 新记忆（tags 保留，lifecycle: "refined"）
  4. memory_delete 删除旧记忆组
  5. memory_quality(rate: 1) 标记新记忆高质量
```

#### 6B 合并（Merge）

将相关但分散的记忆合并为更完整的知识：

```
触发条件：
  - memory_graph 发现关联记忆（connected, max_hops=2）
  - 多条记忆描述同一事物的不同方面

操作：
  1. memory_graph(action="subgraph", radius=2) 找到关联簇
  2. 合并内容，保留每条的独特信息
  3. memory_store 合并后记忆（lifecycle: "refined"）
  4. 旧记忆 memory_update lifecycle: "archived"
```

#### 6C 提升（Promote）

根据使用频率和质量自动提升生命周期：

```
晋升规则：
  raw → refined:   人工 rate(+1) 或 6A/6B 操作后自动
  refined → canonical: quality≥0.8 + 被检索命中≥3次 + 无冲突

操作：
  1. memory_quality(action="analyze", min_quality=0.7) 找候选
  2. 检查 memory_stats 缓存命中次数
  3. memory_update 晋升 lifecycle
```

#### 6D 定期维护（建议每次 Phase 6 执行）

```
1. memory_cleanup()                    → 去重
2. memory_conflicts()                  → 冲突检测
3. memory_quality(action="analyze")    → 质量分布
4. 对 quality<0.5 的记忆执行 6A 压缩
5. 对 raw + 超过 1 周的记忆评估提升或清理
```

详细参数见 [references/mcp-tools.md](references/mcp-tools.md)。

---

## 异常处理

| 场景 | 处理 |
|------|------|
| MCP 失败 | 重试 1 次 → 仍失败降级内存暂存 → 告知用户 |
| 空结果 | 提示存首条或检查 tags |
| 超限截断 | `memory_list` 分页加载 |
| 标签缺失 | 拒绝存储，提示补双标签 |
| 内容冲突 | 展示冲突 → 用户选 → `memory_resolve` |
| 健康失败 | `memory_cleanup` → 仍失败报告用户 |
| 去重相似 | 用户选：跳过/更新/追加 |
| 加载为空 | 跳过注入，不生成空 block |

## Anti-Patterns

- 不存原始对话（用 `memory_harvest`）
- 不跳 tags（无法过滤）
- 不存密钥（memory 未加密）
- 不存重复（定期 `memory_cleanup`）
- 不压缩已加载记忆（`compress` 时原样保留）
- 不存未精炼内容（对话语气词、冗余表述、脱离上下文无法理解的片段）
- 不混用 scope（项目记忆不用 shared/global 标签）
- 不跳过 shared 层（通用技术知识存 shared，不直接存 global）
- 不忽略 lifecycle（定期进化，不让 raw 记忆堆积）

## 迁移说明

已有 `tags=["project", ...]` 格式的记忆仍可正常检索。迁移方式：
- 识别项目名 → `memory_update(tags=["project:<name>", ...])`
- 识别通用技术知识 → `memory_update(tags=["shared", ...])`
- 逐步迁移，无需一次性完成
