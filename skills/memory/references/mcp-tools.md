# Memory MCP 工具参数参考

所有 16 个 memory MCP 工具的完整参数签名。按使用频率排序。

## 核心 CRUD

### memory_store
存储新记忆。必须含 tags。
```
content: string              # 记忆内容（必填）
metadata: {                   # 可选
  tags: string | string[],    # "scope,type" 或 ["scope", "type"]
  type: string                # "note", "decision", "bug" 等
}
conversation_id: string       # 可选，同会话多条去重
```

### memory_search
语义/精确/混合搜索。主检索工具。
```
query: string                 # 搜索词（semantic/exact 必填）
mode: "semantic"|"exact"|"hybrid"  # 默认 semantic
tags: string[]|string         # 标签过滤
limit: int                    # 默认 10，最大 100
quality_boost: float          # 0.0-1.0，默认 0.0
time_expr: string             # "last week", "yesterday", "3 days ago"
after: string                 # ISO date "2026-01-01"
before: string                # ISO date "2026-06-30"
max_response_chars: int       # 截断阈值，防止上下文溢出
include_debug: bool           # 默认 false
```

### memory_list
分页浏览。适合无具体 query 的分类浏览。
```
page: int                     # 1-based，默认 1
page_size: int                # 默认 20，最大 100
tags: string[]                # OR 逻辑（任一匹配）
memory_type: string           # 按 type 过滤
```

### memory_update
更新元数据（不改内容/嵌入）。
```
content_hash: string          # 必填
updates: {
  tags: string[]|string,      # 替换标签
  memory_type: string,        # 更新 type
  metadata: object            # 合并到现有 metadata
}
preserve_timestamps: bool     # 默认 true
```

### memory_delete
灵活删除。支持预览。
```
content_hash: string          # 精确删除（忽略其他过滤）
tags: string[]|string         # 按标签删除
tag_match: "any"|"all"        # 默认 "any"
before: string                # ISO date
after: string                 # ISO date
dry_run: bool                 # 默认 false，true=预览不执行
```

## 批量操作

### memory_cleanup
去重。无参数。
```
无参数
```

### memory_ingest
文档导入。支持 PDF/TXT/MD/JSON。
```
file_path: string             # 单文件模式
directory_path: string        # 目录模式
tags: string[]                # 应用到所有导入记忆
chunk_size: int               # 默认 1000
chunk_overlap: int            # 默认 200
memory_type: string           # 默认 "document"
recursive: bool               # 默认 true
file_extensions: string[]     # 默认 ["pdf","txt","md","json"]
max_files: int                # 默认 100
```

### memory_harvest
从会话记录提取学习。
```
sessions: int                 # 最近 N 个会话，默认 1
session_ids: string[]         # 指定会话 ID
types: string[]               # 过滤：decision, bug, convention, learning, context
min_confidence: float         # 0.0-1.0，默认 0.6
dry_run: bool                 # 默认 true
use_llm: bool                 # 默认 false，需 GROQ_API_KEY
project_path: string          # 覆盖项目路径
```

### memory_store_session
存储完整会话。
```
turns: [{"role": "user"|"assistant", "content": string}]  # 必填
session_id: string            # 可选，稳定 ID
tags: string[]|string         # 自动追加 "session:<id>"
metadata: object              # 额外元数据
```

## 质量管理

### memory_health
数据库健康检查。无参数。
```
无参数 → 返回 version, validation, statistics, integrity, performance
```

### memory_stats
MCP 缓存统计。无参数。
```
无参数 → 返回 hit rate, cache sizes, init times
```

### memory_quality
质量操作。
```
action: "rate"|"get"|"analyze"  # 必填
content_hash: string            # rate/get 必填
rating: "-1"|"0"|"1"           # rate 必填：踩/中性/赞
feedback: string                # rate 可选
min_quality: float              # analyze 可选，默认 0
max_quality: float              # analyze 可选，默认 1
```

## 图与冲突

### memory_conflicts
列出矛盾记忆。无参数。
```
无参数 → 返回冲突对列表
```

### memory_resolve
解决冲突。
```
winner_hash: string   # 必填
loser_hash: string    # 必填
```

### memory_graph
关联图操作。
```
action: "connected"|"path"|"subgraph"  # 必填
hash: string               # connected/subgraph 必填
hash1: string              # path 必填
hash2: string              # path 必填
max_hops: int              # connected，默认 2
max_depth: int             # path，默认 5
radius: int                # subgraph，默认 2
```
