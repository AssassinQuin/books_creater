# 工具调用规范

> **原则：优先 MCP 工具。** SearXNG → GitHub → crawl4ai → 内置 WebSearch/WebFetch → web-search-prime(fallback)。

## 工具优先级总览

| 层级 | 工具 | 最佳场景 |
|------|------|---------|
| **Tier 1 搜索** | `mcp__searxng__searxng_web_search` | 通用搜索、中文、时效性、多引擎聚合 |
| **Tier 1 代码** | `mcp__github__search_repositories`, `search_code`, `get_file_contents` | 开源项目、代码搜索、仓库文档 |
| **Tier 1 爬取** | `mcp__crawl4ai-mcp__scrape`, `crawl`, `crawl_site`, `crawl_sitemap` | JS渲染、递归爬取、全站爬取 |
| **Tier 2 提取** | `mcp__searxng__web_url_read`, `mcp__web_reader__webReader`, `WebFetch` | URL内容提取 |
| **Tier 2 搜索** | `WebSearch`(内置), `mcp__zread__search_doc`, `mcp__zread__read_file` | 补充搜索、GitHub文档搜索 |
| **Fallback** | `mcp__web-search-prime__web_search_prime` | ⚠️ 仅当 Tier 1 全不可用 |

---

## SearXNG 搜索（主力）

### 搜索

```json
{ "query": "关键词 query", "language": "zh", "pageno": 1,
  "time_range": "month", "safesearch": 0 }
```

| 参数 | 说明 |
|------|------|
| query | 关键词（聚合 Google/Bing/DuckDuckGo） |
| language | `"zh"` / `"en"` / `"all"` |
| time_range | `"day"` / `"month"` / `"year"` / 留空 |
| safesearch | `0`无过滤 / `1`适中 / `2`严格 |

### URL 内容提取

```json
{ "url": "https://...", "startChar": 0, "maxLength": 5000 }
```

| 参数 | 说明 |
|------|------|
| section | 提取指定标题下的内容 |
| readHeadings | `true` 只返回标题列表（快速判断结构） |
| paragraphRange | `"1-5"` 指定段落范围 |

---

## crawl4ai 爬取（JS渲染+深度爬取）

### 单页抓取 scrape

```json
{ "url": "https://...", "timeout_sec": 45 }
```

- 浏览器渲染，能处理 JS 动态页面
- 适合 SPA、需要 JS 执行的页面

### 递归爬取 crawl

```json
{ "seed_url": "https://...", "max_depth": 2, "max_pages": 10 }
```

| 参数 | 说明 |
|------|------|
| max_depth | 1-4，BFS 深度 |
| max_pages | 最大页面数 |
| same_domain_only | 默认 true |
| output_dir | 持久化到磁盘（避免上下文膨胀） |

### 全站爬取 crawl_site

```json
{ "entry_url": "https://...", "output_dir": "/path/to/output", "max_depth": 3, "max_pages": 200 }
```

| 参数 | 说明 |
|------|------|
| max_depth | 2-6 |
| max_pages | 最大5000 |
| include_patterns | `["/docs/"]` 只爬匹配路径 |
| exclude_patterns | 排除匹配路径 |

### Sitemap 爬取 crawl_sitemap

```json
{ "sitemap_url": "https://.../sitemap.xml", "output_dir": "/path/to/output", "max_entries": 1000 }
```

---

## GitHub 代码搜索

### 仓库搜索

```json
{ "query": "topic:mcts language:python stars:>100", "sort": "stars", "perPage": 10 }
```

### 代码搜索

```json
{ "query": "content:MCTSNode language:python", "perPage": 10 }
```

### 文件读取

```json
{ "owner": "user", "repo": "project", "path": "README.md" }
```

**前提**：先用搜索发现项目，再用文件读取深挖。

---

## 补充工具

### web-reader

```json
{ "url": "https://...", "return_format": "markdown", "retain_images": true }
```

### WebSearch（内置）

```json
{ "query": "搜索词" }
```

### WebFetch（内置）

```json
{ "url": "https://..." }
```

### zread（GitHub 文档搜索）

```json
{ "repo_name": "owner/repo", "query": "搜索关键词" }
{ "repo_name": "owner/repo", "file_path": "README.md" }
```

---

## 降级链

```
搜索降级: SearXNG → WebSearch → web-search-prime(⚠️fallback)
提取降级: web_url_read → webReader → WebFetch → crawl4ai scrape(JS页面)
代码降级: github API → zread → SearXNG(site:github.com)
爬取降级: crawl_site → crawl → 多次 scrape
```
