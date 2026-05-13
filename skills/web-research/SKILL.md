---
name: web-research
description: >
  多源并行调研 skill。当用户请求包含以下任一意图时必须触发：
  调研、研究、搜索研究、web research、search and analyze、查找资料、
  搜集信息、investigate、study、调研报告、技术调研、方案调研、文献、
  literature review、deep dive、研究报告、技术调研报告、调研分析。
  也包括隐式调研意图：对比分析、生态调研、方案选型、技术选型。
  Workflow: local-first scan → brainstorm → parallel search → summarize → persist.
  Output: structured research report in {skill_dir}/data/.
user-invocable: true
allowed-tools:
  - mcp__searxng__searxng_web_search
  - mcp__searxng__web_url_read
  - mcp__crawl4ai-mcp__scrape
  - mcp__crawl4ai-mcp__crawl
  - mcp__crawl4ai-mcp__crawl_site
  - mcp__crawl4ai-mcp__crawl_sitemap
  - mcp__web_reader__webReader
  - mcp__github__search_repositories
  - mcp__github__search_code
  - mcp__github__get_file_contents
  - mcp__github__list_commits
  - mcp__zread__search_doc
  - mcp__zread__read_file
  - mcp__zread__get_repo_structure
  - mcp__web-search-prime__web_search_prime
  - WebSearch
  - WebFetch
  - Agent
  - Grep
  - Glob
  - Read
  - Bash
  - mcp__memory__memory_search
  - mcp__memory__memory_store
---

# Web Research Skill (Claude Code)

多源并行调研：本地优先 → 头脑风暴 → 搜索 → 综合 → 持久化。

**MANDATORY 语言：面向用户中文。每个发现必须可追溯真实来源。**

## 核心原则

| 优先级 | 规则 |
|--------|------|
| 信息来源 | skill目录已有 → 项目目录已有 → memory已有 → 网络搜索 |
| 工具优先级 | SearXNG → GitHub API → crawl4ai → WebSearch/WebFetch → web-search-prime(fallback) |
| 保存位置 | 原始数据+最终报告统一存 `{skill_dir}/data/`（跨项目复用） |

## 工具体系

### 四类工具

| 类 | 主工具 | 最佳场景 |
|----|--------|---------|
| **搜索** | `mcp__searxng__searxng_web_search`, `WebSearch` | 通用搜索、中文、时效性 |
| **提取** | `mcp__searxng__web_url_read`, `mcp__web_reader__webReader`, `WebFetch` | URL内容提取、markdown转换 |
| **爬取** | `mcp__crawl4ai-mcp__scrape`, `crawl`, `crawl_site`, `crawl_sitemap` | 单页渲染(JS)、递归爬取、全站爬取 |
| **代码** | `mcp__github__search_repositories`, `search_code`, `get_file_contents` | 开源项目发现、代码搜索、仓库文档 |

### 工具选择决策树

```
需要什么？
├─ 搜索信息 → SearXNG(language匹配) → WebSearch(补充)
├─ 提取URL内容 → web_url_read(轻量) → webReader(备用) → WebFetch(兜底)
├─ JS渲染页面 → crawl4ai scrape(浏览器渲染)
├─ 爬整个文档站 → crawl4ai crawl_site → crawl_sitemap
├─ 递归探索链接 → crawl4ai crawl(max_depth)
├─ 找开源项目 → github search_repositories → search_code
├─ 读仓库文件 → github get_file_contents → zread read_file
└─ 以上全不可用 → web-search-prime(fallback,标注⚠️)
```

## 流程概览

```
Phase 0: 快速判定    → 小查询直接答 / 深度调研走完整流程
Phase 1: 本地优先    → skill目录 → 项目目录 → memory（任一命中可短路）
Phase 2: 头脑风暴    → 搜索主题 + 工具分配 + 🔒确认
Phase 3: 并行搜索    → ≤3 子agent(general-purpose)分工搜索
Phase 4: 综合+持久化 → 去重 → 总结 → 🔒确认 → 保存
```

---

## Phase 0: 快速判定

| 信号 | 判定 | 路径 |
|------|------|------|
| 单一事实（"Exa pricing是什么"） | 快速查询 | 直接用 SearXNG 或 WebSearch 搜1-2次，返回答案+来源，不进完整流程 |
| 爬取任务（"爬取XX文档站"） | 爬取型 | 直接用 crawl4ai crawl_site/crawl，跳到 Phase 4 保存 |
| 对比/分析/多角度/调研 | 深度调研 | 进 Phase 1 |

---

## Phase 1: 本地优先扫描

**目标**：复用已有研究，避免重复搜索。按优先级依次扫描，任一级命中可短路。

### 1.1 Skill 目录扫描

```
glob(pattern="{skill_dir}/data/**/*.md")
grep(pattern="{关键词}", path="{skill_dir}/data/")
```

命中 → 读取 → 展示摘要 → 🔒询问："直接复用 / 增量更新 / 重新开始"

### 1.2 项目目录扫描

```
glob(pattern="{project_root}/docs/**/*.md")
grep(pattern="{关键词}", path="{project_root}/docs/")
```

### 1.3 Memory 检索

```
mcp__memory__memory_search(query="{研究主题}", limit=10)
```

### 1.4 无命中

直接进 Phase 2。

---

## Phase 2: 头脑风暴与搜索方案

### 2.1 搜索主题

基于 Phase 1 上下文 + 用户需求，生成 3-6 个搜索主题：

```markdown
1. **{主题A}** — {为什么相关，期望找到什么}
2. **{主题B}** — ...
```

### 2.2 工具分配

| 主题类型 | 搜索工具 | 提取工具 | 交叉验证 |
|----------|---------|---------|---------|
| 中文内容 | SearXNG(language=zh) | web_url_read / webReader | WebSearch(英文交叉) |
| 英文技术 | SearXNG(language=en) / WebSearch | crawl4ai scrape / webReader | GitHub |
| 代码/开源 | github search_repositories + search_code | github get_file_contents | SearXNG(site:github.com) |
| 时效性新闻 | SearXNG(time_range=day/week) | web_url_read | — |
| 文档站深度 | — | crawl4ai crawl_site / crawl_sitemap | — |
| 综合调研 | SearXNG + GitHub + WebSearch | crawl4ai + webReader | 交叉验证 |

**每主题至少 2 个来源交叉验证。**

### 2.3 预算

默认 30 次工具调用（3 agents × 10次/agent）。超限停止→标注"未完成"→进 Phase 4。

### 2.4 🔒 用户确认

展示：主题列表 + 工具方案 + 预估调用数。确认后进 Phase 3。

---

## Phase 3: 并行搜索

最多 **3 个子agent** 并行，使用 `Agent` 工具，`subagent_type: "general-purpose"`。

### 3.1 分工方案

所有子agent共享相同的 MCP 工具。**按搜索主题分工**，而非按工具链分工：

| Agent | 职责 | 推荐工具组合 |
|-------|------|------------|
| Agent 1 | 主题A+B 搜索+提取 | SearXNG + web_url_read + webReader |
| Agent 2 | 主题C 代码/开源 | GitHub search + get_file_contents + zread |
| Agent 3 | 交叉验证+补充 | WebSearch + crawl4ai scrape + SearXNG |

### 3.2 🔴 MANDATORY 子 Agent Prompt 模板

**orchestrator 必须将以下模板注入子 agent prompt。`{...}` 替换为实际值，其余一字不改。**

---

你是调研子 agent。你的任务是用指定工具收集研究资料。

**研究主题**: {主题名}
**分配工具**: {工具组合描述}

### 工具调用规范

**SearXNG 搜索** `mcp__searxng__searxng_web_search`:
- 参数: `{"query": "关键词", "language": "zh或en", "pageno": 1, "safesearch": 0, "time_range": "month"}`
- query 用关键词，中文搜中文 query，英文搜英文 query

**SearXNG 内容提取** `mcp__searxng__web_url_read`:
- 参数: `{"url": "https://...", "maxLength": 5000}`
- 支持 section/paragraphRange 精准提取

**crawl4ai 单页抓取** `mcp__crawl4ai-mcp__scrape`:
- 参数: `{"url": "https://...", "timeout_sec": 45}`
- 支持浏览器渲染（JS页面），比普通提取更可靠

**crawl4ai 递归爬取** `mcp__crawl4ai-mcp__crawl`:
- 参数: `{"seed_url": "https://...", "max_depth": 2, "max_pages": 10}`
- 适合从一页出发递归探索

**web-reader 提取** `mcp__web_reader__webReader`:
- 参数: `{"url": "https://...", "return_format": "markdown"}`

**WebSearch** (内置):
- 参数: `{"query": "搜索词"}`

**WebFetch** (内置):
- 参数: `{"url": "https://..."}`

**GitHub 仓库搜索** `mcp__github__search_repositories`:
- 参数: `{"query": "topic:x language:y stars:>100", "sort": "stars", "perPage": 10}`

**GitHub 代码搜索** `mcp__github__search_code`:
- 参数: `{"query": "content:xxx language:python", "perPage": 10}`

**GitHub 文件读取** `mcp__github__get_file_contents`:
- 参数: `{"owner": "user", "repo": "project", "path": "README.md"}`

### 工具优先级

1. 优先使用 SearXNG / GitHub / crawl4ai / webReader
2. ⚠️ 只有当以上工具全部返回空结果或报错时，才使用 `mcp__web-search-prime__web_search_prime`
3. 如果使用 web-search-prime，输出中标注 `⚠️ fallback`

### 执行步骤

1. 为每个搜索主题构造 2-3 个 query，调用搜索工具（每 query 取 top 5-10 结果）
2. 从搜索结果中选出 2-3 个高相关 URL，用提取工具获取全文
3. 某工具返回空/报错 → 立即换另一个工具重试
4. 所有结果按以下格式输出

### 🔴 输出格式（MANDATORY）

每个搜索结果必须包含完整 5 个字段：

```markdown
### 来源 1: {标题}
- **URL**: {完整URL}
- **工具**: {实际调用的工具名}
- **Query**: {实际使用的搜索 query}
- **相关性**: 高/中/低
- **摘要**: {2-3句话概括内容}
```

如果提取了全文，额外添加：
```markdown
- **全文要点**: {关键要点，3-5条}
```

### 约束

1. 中文输出
2. 只返回与主题相关的结果，过滤噪音
3. 每条结果必须包含 **URL + 工具名 + Query**（可追溯性）
4. 所有搜索工具都无结果时，输出：`⚠️ 未找到相关结果。已尝试的 query: [列出]`

---

### 3.3 orchestrator 职责

1. **原样注入** 3.2 的模板到每个子 agent prompt（仅替换 `{...}` 占位符）
2. **收集所有子 agent 输出后**，验证每条结果是否包含 URL/工具/Query/相关性/摘要
3. 格式不合格时：要求重试一次；仍不合格则标记 `⚠️ 格式不完整` 纳入 Phase 4

---

## Phase 4: 综合 + 持久化

### 4.1 去重去噪

URL去重 | 内容去重（多来源合并标注） | 噪音过滤 | 过滤格式不完整的结果

### 4.2 综合报告

基于搜索结果生成结构化报告，输出结构：

1. **背景与目标**
2. **核心发现**（每条标注 [来源#N]）
3. **方案对比**（仅对比型调研时包含，用表格）
4. **结论与建议**
5. **信息源列表**（所有 URL + 来源编号）

规则: 中文 | 交叉验证标注 [来源A,B验证] | 知识空白标 ⚠️ | 不编造

### 4.3 🔒 用户确认

展示报告。选项：✅确认 / 🔄补充搜索(回Phase 2) / ✏️修改 / ❌放弃

### 4.4 持久化

**保存到 skill 目录**（权威位置，跨项目复用）：

```
{skill_dir}/data/{YYYYMMDD}-{topic-slug}/
├── 研究报告.md
├── raw/
│   ├── agent-a.md
│   ├── agent-b.md
│   └── sources-index.md
```

**Memory 存储**（概述，可定位）：

```
content: "{主题}研究: {概述，含关键发现和结论}。详情: {skill_dir}/data/{slug}/"
tags: "global,reference"
```

---

## 异常处理

| 异常 | 处理 |
|------|------|
| SearXNG 不可用 | 降级到 WebSearch → crawl4ai scrape → web-search-prime(标注⚠️) |
| GitHub search 无结果 | 放宽条件（去掉 stars/language 过滤），或 SearXNG 搜 `site:github.com` |
| crawl4ai 超时 | 增加 timeout_sec 到 120；仍失败用 web_url_read 替代 |
| JS渲染页面提取失败 | crawl4ai scrape（有浏览器渲染）替代 web_url_read |
| 全文提取失败 | 保留搜索摘要，标注"无法提取全文" |
| 子agent超时 | 收集已完成结果，标注"部分搜索" |
| 子agent输出格式不合规 | 标记 `⚠️ 格式不完整`，仍纳入 Phase 4 |
| 无搜索结果 | 调整query重试一次→仍无则报告 |
| 用户中断 | 保存已有结果到skill目录 |
| skill_dir不存在 | 用 mkdir -p 创建 |
