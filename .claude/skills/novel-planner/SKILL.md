---
name: novel-planner
description: 小说卷规划，含全书总纲、逐卷环境先行设计、章节场景清单和跨卷伏笔。触发词：规划卷/大纲/卷大纲
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__relation_list, mcp__novel-db__volume_create, mcp__novel-db__volume_list, mcp__novel-db__volume_get, mcp__novel-db__volume_update, mcp__novel-db__chapter_plan, mcp__novel-db__scene_create, mcp__novel-db__scene_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_list, mcp__novel-db__world_upsert
lifecycle: core
---

# 小说卷规划

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`
> 环境引擎：读 `.claude/skills/novel-writer/references/engine-environment.md`
> 快照引擎：读 `.claude/skills/novel-writer/references/engine-snapshot.md`
> **因果逻辑大纲法**: 读 `.claude/skills/novel-writer/references/causal-outline-method.md`
> **术语定义**: 读项目根目录 `NOVEL-CONTEXT.md`

<what-to-do>
## 强制流程

```
B1: 召回数据 → 全书总纲(首卷) → 🔒确认 → 逐卷规划(环境先行) → 🔒卷确认 → 章节场景(含快照) → 跨卷伏笔 → commit
```

每卷规划完必须 🔒确认 才能进入章节场景创建。用户说"改"→ 回退修改。
</what-to-do>

<supporting-info>

## B1: 卷规划

触发: "规划卷"/"大纲" | 前置: A层完成

1. 召回：`novel_get` + `world_query` + `character_list` + `relation_list` + 已有 `volume_list`

2. 如果是第一卷 → 先生成**全书总纲**（一页纸）：
   - 核心冲突 + 终极方向
   - 预计卷数（百万字≈500章/8-15卷）
   - 主角成长弧线关键节点
   - 明暗双线全局规划（暗线分几层揭示）
   - **全书因果逻辑网**：主线因果链 + 暗线因果链 + 世界观刑具压迫曲线 + 不可逆节点分布
   - 🔒**用户确认总纲**后才继续

3. **逐卷规划**（环境先行 + 因果逻辑网）：
   ```
   volume_create(novel_id, number=N, title="卷名",
     main_plotlines=[{name, description, purpose}, ...],
     notes="伏笔埋设计划/配角出场安排/升级节点/替代爽点")
   ```

   每卷必定义：主线推进 + 暗线揭示 + 重点配角弧光 + 升级/爽点 + 伏笔计划 + 卷尾状态

   **因果逻辑网构建（每卷必做）**：
   1. **卷级因果链**：触发事件 → 核心冲突 → 不可逆节点 → 遗留后果
   2. **逐日因果网**：每个事件必须回答「因为什么→所以什么→逼出什么→雪球什么」
   3. **世界观刑具化**：本卷中世界观规则如何对角色产生持续压迫？
   4. **不可逆节点确认**：本卷是否有角色做出无法回头的选择？
   5. **遗留后果设置**：本卷结束时留给下卷的「定时炸弹」是什么？

   **禁止时间驱动写法**：不写「D1主角去了X→D2主角遇到Y」，写「因为D1的Z后果，主角被迫在D2做出A选择，而世界观规则B使得这个选择必然引发C」

### 环境先行设计（每卷必做）

1. 识别本卷主要场景地点（2-5个）
2. 每个地点按 `engine-environment.md` 5要素建立档案
3. `world_upsert(category="location", name="{地点名}", data={环境档案})`
4. 环境设计完成后，再规划事件

4. **大纲验证（强制）**：三Agent审查 → P0必须修复 → 🔒通过后进入场景

5. 章节场景清单（含快照）：
   ```
   chapter_plan + scene_create
   场景快照（≤200字）: 地点/时间/人物/物品/目的/环境
   ```

6. 跨卷伏笔：`foreshadow_plant(...)`
7. `git commit -m "B1: 第{N}卷规划完成"`

---

## 大纲更新

触发: 用户在写作过程中想修改某卷规划

1. `volume_get(volume_id)` 读取当前规划
2. 修改 → `volume_update(volume_id, ...)`
3. 标注受影响章节 → 提醒用户
4. `git commit -m "更新: 第{N}卷大纲调整"`

---

## 断点续传

触发时先检查 `memory_search(query="flow-state", tags=["project:{名},flow-state"])`
有记录 → "上次我们在{步骤}暂停了，从那里继续？"

</supporting-info>
