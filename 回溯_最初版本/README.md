# 回溯：最初的 book MCP 与最初版小说 skill

> 提取时间：2026-08-27。所有文件来自 git 历史，工作区中原件已删除（novel-db-mcp 于 2026-06-29 提交 `17e61a9`「尝试」中整体移除）。

## mcp最初版/

| 文件 | 来源提交 | 日期 |
|------|---------|------|
| mcp-2026-05-01-最早配置.json | `969a7f1` chore: add MCP server config | 2026-05-01 23:26 |
| mcp-2026-05-17-v1.0配置.json | `f264cd6` v1.0 | 2026-05-17 14:49 |
| server.py（3407 行） | `f264cd6` v1.0 | 2026-05-17 |
| 001_init_schema.sql（201 行） | `f264cd6` v1.0 | 2026-05-17 |
| requirements.txt | `f264cd6` v1.0 | 2026-05-17 |

说明：
- **2026-05-01 的最早配置**只引用了仓库外路径 `/Users/ganjie/skills/novel-db-mcp/server.py`（macOS 本机），服务端代码当时未入库，该版本已不可恢复。
- **2026-05-17 "v1.0"** 是服务端代码入库的第一个版本，也是可回溯的最早完整版本。FastMCP 3.x + PostgreSQL，约 40 个工具，12 张表。

## skill最初版/

来源提交 `508aa8f` feat: init novel-writer skill with 9 files（2026-05-01 22:53）：

- SKILL.md（408 行）— 7 阶段全流程：灵感/头脑风暴 → 世界观（6 维）→ 人物 → 大纲 → 逐章写作 → 三 Agent 并行审阅 → 平台上架；Memory MCP 管状态、git 逐阶段提交
- references/brainstorm-guide.md（90 行）
- references/worldbuilding-template.md（181 行）
- references/character-design.md（150 行）
- references/writing-style.md（124 行）
- references/anti-ai-patterns.md（104 行）
- references/review-checklist.md（139 行）
- references/platform-rules.md（117 行）
- references/genre-profiles.md（92 行）
- 网文AI创作流水线-可操作流程.md（305 行，原路径 docs/）

## 关键节点时间线

1. 2026-05-01 `508aa8f` novel-writer skill 初始化（9 文件），状态存 Memory MCP
2. 2026-05-01 `969a7f1` .mcp.json 引入 novel-db（指向仓库外 macOS 路径）
3. 2026-05-01 `6a6adf4` R1 整合 novel-db MCP（SKILL.md 重写，Memory 调用改为 novel-db 调用）
4. 2026-05-02 `3c35544` 新增 3 个编排工具引用（writing_start / rule_detail / record_new_content）
5. 2026-05-17 `f264cd6` 服务端代码首次入库（v1.0，3407 行）
6. 2026-06-29 `17e61a9` novel-db-mcp 整体删除，转向纯文件流 + story-* skills 体系
