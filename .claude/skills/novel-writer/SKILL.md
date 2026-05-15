---
name: novel-writer
description: 网文创作总路由器。触发词：写小说/帮我写/上架/进度/状态/搜一下
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*
lifecycle: core
---

# 网文创作总入口

> 术语定义→`NOVEL-CONTEXT.md` | 写作架构→`novel-chapter-writer` Multi-Agent Pipeline

<what-to-do>

## 意图路由（优先级：C3 > B2 > 模糊匹配）

| 关键词 | Skill | 说明 |
|--------|-------|------|
| 头脑风暴/灵感/建世界观/设定/加物品 | novel-setup | A1/A2/物品设计 |
| 设计人物/加人物/人物卡/改人物 | novel-character | 7步蒸馏+外观+对话 |
| 规划卷/大纲/卷大纲 | novel-planner | Multi-Agent Pipeline 4子Agent |
| 写第N章/继续写/写一章 | novel-chapter-writer | 4子Agent流水线写作 |
| 审阅/检查/诊断/卡文/改设定/OOC | novel-qa | 15维度扫描+健康诊断 |
| 写战斗/战斗场景/战斗设计 | novel-battle | 分镜+弧线+燃点+审计 |
| 修复/去重/批量改/修文/润色 | novel-reviser | 模式去重+连续性修复 |
| 上架/发布 | **本skill** | 见下方「平台上架」 |
| 进度/状态/加素材/拆书 | **本skill** | 见下方「状态查询/素材/拆书」 |
| 搜一下/查{关键词} | **本skill** | `db_search(novel_id, keyword)` |
| 无匹配 | **本skill** | `novel_get`+`chapter_list`查进度→建议下一步 |

</what-to-do>

<supporting-info>

## 平台上架

1. `novel_get(novel_id)` → `world_query(novel_id)` 收集项目数据
2. 合规检查（字数/章节数/简介完整性）
3. 输出到 `novels/{小说名}/上架版/`
4. 参考 `references/platform-rules.md`

## 状态查询

```
novel_get(novel_id) → 项目基础信息
volume_list(novel_id) → 卷列表
chapter_list(novel_id) → 章节列表（含状态）
foreshadow_list(novel_id) → 伏笔状态
character_list(novel_id) → 人物列表
health_check(novel_id) → 健康诊断（伏笔积压/配角活跃/升级节奏/日常密度/暗线推进/卷完成度）
```

## 素材与拆书

- 灵感/素材 → `memory_store(tags="shared,material")`
- 新AI味模式 → `memory_store(tags="shared,anti-ai-pattern")`
- 拆书 → 读 `references/book-analysis-guide.md` → 段落拆解+技巧提取 → `memory_store` → 写入 `novels/拆书笔记/`

## 边界条件

- **novel_id 未指定** → `novel_list()` 展示项目列表让用户选
- **数据库连接失败** → 提示检查 PostgreSQL 服务状态
- **无匹配且无任何项目** → 引导用户先执行 `novel-setup` 创建项目

</supporting-info>
