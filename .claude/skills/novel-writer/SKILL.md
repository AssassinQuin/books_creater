---
name: novel-writer
description: 百万字网文创作引擎总路由器。根据用户意图分发到对应子技能，处理上架/进度/素材查询。触发词：写小说/帮我写/上架/进度/加素材
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*, mcp__memory__*
lifecycle: core
---

# 百万字网文创作引擎

> 总路由器：识别用户意图 → 分发到对应子技能。不直接执行创作。

<what-to-do>

## 路由规则

| 用户意图 | 触发词 | 分发目标 |
|---------|--------|---------|
| 头脑风暴/灵感 | "头脑风暴"/"灵感" | novel-setup (A1) |
| 建世界观/设定 | "建世界观"/"设定"/"加物品" | novel-setup (A2) |
| 设计人物 | "设计人物"/"加人物"/"改人物" | novel-character (A3) |
| 全书大纲 | "规划全书"/"设计大纲"/"全书框架" | novel-planner (B1) |
| 卷级大纲 | "设计卷"/"卷大纲"/"章节规划"/"事件设计" | novel-planner-volume (B1) |
| 写章节 | "写第N章"/"继续写"/"写一章" | novel-chapter-writer (B2) |
| 审阅/检查 | "审阅"/"检查"/"诊断"/"OOC"/"卡文" | novel-qa (B3/C2/C3) |
| 修复/润色 | "修复"/"去重"/"修文"/"润色" | novel-reviser |
| 上架/发布 | "上架"/"发布" | C1流程（见下方） |
| 进度/状态 | "进度" | 状态查询（见下方） |
| 加素材 | "加素材" | 素材入库（见下方） |

## 冲突消歧

当用户意图可能匹配多个子技能时，按以下优先级处理：C3（级联更新）> B2（章节写作）> 其他阶段。原因在于级联更新涉及设定变更的全局影响，需要优先响应；章节写作是核心产出环节，次之。

## C1: 上架流程

```
1. 确认目标平台（番茄/起点/纵横）
2. skill_loader("novel-writer", "engine", "platform") 加载平台规则
3. 检查合规性（违禁词/字数/章节结构）
4. 格式化输出
5. 发布前与用户确认，避免误操作导致内容提前公开
```

## 状态查询

```
volume_list(novel_name="这次不一样了") → 卷完成度
chapter_list(novel_name="这次不一样了") → 章节状态统计
foreshadow_list(novel_name="这次不一样了") → 伏笔回收率
health_check(novel_name="这次不一样了") → 健康指标
```

## 素材入库

```
memory_store(content, tags=["project:books_creater", "material"])
```

</what-to-do>

<supporting-info>

## 子技能速查

| Skill | 阶段 | 核心输出 |
|-------|------|---------|
| novel-setup | A1/A2 | 项目创建+世界观 |
| novel-character | A3 | 人物蒸馏+入库 |
| novel-planner | B1(全书) | 框架+脉络+卷级目标卡 |
| novel-planner-volume | B1(卷级) | 逐章大纲+事件架构 |
| novel-chapter-writer | B2 | 正文(Multi-Agent Pipeline) |
| novel-qa | B3/C2/C3 | 审阅+诊断+级联更新 |
| novel-reviser | 修订 | 批量修复+润色 |

## 当前项目

《这次不一样了》— novel_name: "这次不一样了", 14卷+尾声, 玄幻网文

</supporting-info>
