---
name: novel-writer
description: 网文创作总入口 — 路由到子skill，处理上架和状态查询。触发词：写小说/我要写/帮我写/上架/发布/番茄/起点/进度/状态/status/加素材/拆书。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__novel_get, mcp__novel-db__novel_list, mcp__novel-db__novel_update, mcp__novel-db__novel_delete, mcp__novel-db__world_query, mcp__novel-db__chapter_list, mcp__novel-db__volume_list, mcp__novel-db__foreshadow_list, mcp__novel-db__character_list, mcp__novel-db__db_search, mcp__memory__memory_store, mcp__memory__memory_search
---

# 网文创作总入口

> 共享约定（铁律/数据分层/Memory模型/Git规范）：读 `references/shared-conventions.md`

## 意图路由

```
关键词                                          → 调用 Skill
────────────────────────────────────────────────────────────
"头脑风暴"/"灵感"/"建世界观"/"设定"/"加物品"     → novel-setup
"设计人物"/"加人物"/"人物卡"/"改人物"             → novel-character
"规划卷"/"大纲"/"卷大纲"                         → novel-planner
"写第N章"/"继续写"/"写一章"                      → novel-chapter-writer
"审阅"/"检查"/"诊断"/"卡文"/"改设定"/"OOC"       → novel-qa
"写战斗"/"战斗场景"/"战斗设计"/"检查战斗"         → novel-battle
"修复"/"去重"/"批量改"/"修文"/"润色"             → novel-reviser
"上架"/"发布"/"番茄"/"起点"                      → C1 本skill处理
"进度"/"状态"/"加素材"/"拆书"                    → D 本skill处理
无匹配 → novel_get + chapter_list 查进度，建议下一步
```

### 冲突消歧优先级（从高到低）

1. **C3级联更新**（"改设定"/"改人物"）→ novel-qa — 立即处理，防止脏数据扩散
2. **B2写作中断**（写作中说"改设定"）→ 暂停写作，建议 `/novel-qa` 处理后回来
3. **A层重建** → 按用户意图路由，不强制顺序
4. **模糊匹配** → "帮我写"无上下文时，查 `novel_list` 问用户要操作哪个项目

---

## C1: 平台上架

触发: "上架"/"发布"

1. 读 `references/platform-rules.md`
2. 从 `novel_get` + `world_query` 获取项目数据
3. 合规检查 + 降AI率 + 排版适配
4. 输出到 `novels/{小说名}/上架版/`

---

## D: 查询

### 状态总览

触发: "进度"/"状态"

```
novel_get + volume_list + chapter_list + foreshadow_list + character_list
→ 项目名/阶段/卷进度/章节数/人物数/伏笔回收率/最近章节
```

### 素材操作

触发: "加素材"
- 内容 → `memory_store(tags="shared,material")`
- 新AI味 → `memory_store(tags="shared,anti-ai-pattern")`

### 拆书分析

触发: "拆书"/"分析小说"

读 `.claude/skills/novel-writer/references/book-analysis-guide.md`

1. 用户导入小说文本（粘贴或文件路径）
2. **段落拆解**：按场景/对话/描写/动作/心理分类
3. **技巧提取**：
   - 节奏：句长分布、段落长度变化
   - 对话：占比、潜台词密度、废话比例
   - 描写：五感使用频率、侧面描写占比
   - 伏笔：前置线索与后置揭示的章距
4. **风格建档**：提取的文风特征 → `memory_store(tags="shared,style-profile", type="reference")`
   - 句式偏好（短/中/长占比）
   - 对话占比均值
   - 描写密度（每千字描写段数）
   - 独特用词/口头禅
5. **可用技巧**：可直接借鉴的手法 → `memory_store(tags="shared,technique")`
6. 写入报告 → `novels/拆书笔记/{书名}.md`

---

## 全局数据搜索

触发: "搜一下"/"查一下{关键词}"

```
db_search(novel_id, keyword) → 跨世界观/人物/章节/伏笔/时间线搜索
```
