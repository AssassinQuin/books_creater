---
name: novel-qa
description: 小说全链路质量保障。触发词：审阅/检查/诊断/改设定/OOC/卡文
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*
lifecycle: quality
---

# 小说质量保障

<what-to-do>

## 强制流程

```
B3审阅: 加载上下文 → 3Agent并行扫描 → 🔒评分卡 → 汇总报告 → 存盘
C4设定审查: 全量加载 → 6维度审查 → 🔒问题清单 → 修复 → 级联同步
C2诊断: health_check → 指标对比 → 🔒破局方案
C3更新: 改数据 → db_search找影响 → 🔒确认 → 执行 → 验证
```

输出到 `novels/{小说名}/审阅报告/`。无文件输出 = 流程未完成。

## 问题分级标准

| 级别 | 判定标准 | 处理要求 |
|------|---------|---------|
| P0-致命 | 因果链断裂/人物OOC/设定矛盾/违禁词 | 必须修复，阻断发布 |
| P1-严重 | 伏笔未回收/节奏断层/质量方差超限 | 必须修复，限1轮内 |
| P2-中等 | 描写冗余/对话平淡/爽点不足 | 建议修复，可延期 |
| P3-轻微 | 标点不均/用词重复/格式不统一 | 可选修复，批量处理 |

</what-to-do>

<supporting-info>

## B3: 大纲审阅（触发：审阅大纲）

加载：`skill_loader("novel-qa", "engine", "outline-review")`

Phase 1: 10维度Agent审计（结构/起承转合/伏笔密度/人物弧光/支线检验/情绪曲线/悬念密度/世界观一致性/因果链/可读性）
- 因果链断裂 → 自动判P0，参考 `skill_loader("novel-qa", "engine", "causality")`
Phase 2: P0/P1修复（每问题3方案+代价评估）
Phase 3: 重评，综合≥85通过，最多3轮

## B3: 正文审阅（触发：审阅正文/校对）

Step 1: 加载角色状态（`character_get` + `chapter_get_context`）
Step 2: 3Agent并行扫描
  - Agent-人物: OOC检测/知识矛盾/说话风格一致性/关系合理性
  - Agent-逻辑: 时间线连贯/经济系统一致/伏笔回收状态/物品使用逻辑
  - Agent-质量: 战斗场面质量/章节结构/爽点分布/NPC活跃度/写作风格/AI指纹(F1-F6)
Step 3: `validate_chapter(chapter_text)` 硬约束复核（写时自检的补充，不替代）
Step 4: 问题分级 P0/P1/P2/P3
Step 5: 输出审阅报告 → 评级 A(≥90)/B(≥80)/C(≥70)/D(<70)

AI指纹检测：`skill_loader("novel-qa", "engine", "anti-ai")`

## C4: 设定审查（触发：审设定）

1. `world_query` + `character_list` + `relation_list` + `foreshadow_list` 全量加载
2. 6维度审查：内部自洽/人物一致/物品合理/历史可信/关系完整/伏笔可行
3. 🔒问题清单 → 修复方案 → 执行 → 级联同步（受影响的章节/人物/伏笔）

## C2: 健康诊断（触发：诊断/卡文）

`health_check(novel_id)` → 6指标：伏笔积压率/配角活跃gap/升级节奏/日常密度/暗线推进/卷完成度
→ 低于阈值项 → 破局策略（加事件/减日常/回收伏笔/激活配角）

## C3: 级联更新（触发：改设定/改人物）

1. 更新数据
2. `db_search(novel_id, 关键词)` 扫描全部影响范围
3. 🔒确认修改清单（影响章节/人物/伏笔/时间线）
4. 执行修改
5. 验证一致性

## 审计工具加载

`skill_loader("novel-qa", "engine", "item")` 物品一致性
`skill_loader("novel-qa", "engine", "causality")` 因果逻辑审计
`skill_loader("novel-qa", "engine", "anti-ai")` AI指纹检测

</supporting-info>
