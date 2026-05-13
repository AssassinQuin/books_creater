---
name: novel-battle
description: 战斗场面引擎，含分镜设计、战斗弧线、燃点设计和八维度审计。触发词：写战斗/战斗场景/战斗审计
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__novel_get, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_list, mcp__novel-db__chapter_list, mcp__novel-db__foreshadow_list, mcp__novel-db__timeline_query, mcp__novel-db__world_query
lifecycle: quality
---

# 战斗场面引擎

> 共享约定：读 `references/shared-conventions.md`
> 动作引擎：读 `references/engine-action.md`
> **术语定义**: 读项目根目录 `NOVEL-CONTEXT.md`

<what-to-do>
## 核心公式

```
短动作句(快) → 慢镜头长句(关键击) → 反馈/后果 → 下一循环
铺垫(70%) → 转折(5%) → 爆发(15%) → 余波/代价(10%)
```

## 强制4步流程

```
Step 1 战斗设计 → Step 2 分镜脚本 → Step 3 写正文 → Step 4 审计
```
</what-to-do>

<supporting-info>

## Step 1: 战斗设计

### 1.1 战况分析

读取角色状态（蒸馏文件 + 角色深化 + novel-db），确定POV角色。

### 1.2 战场环境设计

参照 `engine-environment.md`：具体位置 + 可用元素 + 5感。

### 1.3 异兽行为设计

每种异兽≥1独特行为 + ≥1独特弱点 + ≥1独特攻击方式。同场多只同等级必须有行为差异。

### 1.4 战斗弧线

铺垫(70%) → 转折(5%) → 爆发(15%) → 代价(10%)

### 1.5 燃点设计（每场≥1个）

绝地反击 / 团队配合 / 能力觉醒 / 代价高光 / 环境杀。燃点必须绑定角色情感。

---

## Step 2: 分镜脚本

| # | 机位 | 时长 | 内容 | 字数 | 节奏 |
|---|------|------|------|------|------|
| 1 | 远景 | 3s | 全战场/态势/紧迫 | 100-150 | 慢 |
| 2 | 中景 | 2s | 对峙/试探/首次交锋 | 80-120 | 中 |
| 3 | 快切 | 0.3s×N | 密集战斗/被压制 | ≤15字/句 | 快 |
| 4 | 慢镜头 | 5s | 转折/致命击/死亡 | 200-300 | 极慢 |
| 5 | 特写 | 1s | 微表情/碰撞/关键细节 | 50-80 | 定格 |

**段落长度 = 时间流速** — 战斗节奏的核心技法。

---

## Step 3: 写正文

### 强制规则

1. **POV锁定**: 一场战斗一个POV
2. **动作-反馈链**: 每一击必须有结果
3. **动词>形容词**: 消除"副词+动词"组合
4. **辅助描写≤10字**: 战斗中压缩心理/环境
5. **五感反馈**: 触/声/嗅/味
6. **实时代价**: 持续展示消耗，不是最后总结
7. **受伤+物品记录（战后强制）**: 写入角色蒸馏文件和DB
8. **20%细节法则**: 只给关键细节，让读者想象80%

---

## Step 4: 八维度审计

分镜完整性 / POV一致性 / 动作-反馈链 / 异兽差异化 / 代价系统 / 燃点审计 / 节奏审计 / 精准动词审计

评分: A(全满足) / B(1-2处小不足) / C(3+处不足) / D(核心规则违反)

C级以下必须修改才能合并入章节正文。

---

## 协作模式

- 与chapter-writer协作：写完→有战斗→调本skill→整合→全章检查
- 与novel-qa协作：正文扫描时战斗维度→调本skill审计

</supporting-info>
