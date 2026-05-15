---
name: novel-battle
description: 战斗场面引擎。触发词：写战斗/战斗场景/战斗审计
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__*
lifecycle: quality
---

# 战斗场面引擎

<what-to-do>

## 核心公式

```
短动作句(快) → 慢镜头长句(关键击) → 反馈/后果 → 下一循环
铺垫70% → 转折5% → 爆发15% → 余波/代价10%
```

## 强制4步流程

```
Step 1 战斗设计 → Step 2 分镜脚本 → Step 3 写正文 → Step 4 审计
```

</what-to-do>

<supporting-info>

## Step 1: 战斗设计

- **角色读取**: `character_get(id)` 获取POV状态/能力
- **战场环境**: `skill_loader("novel-battle", "engine", "environment")` → 位置+元素+5感
- **异兽行为**: 每种≥1独特行为+弱点+攻击方式
- **燃点**: 绝地反击/团队配合/能力觉醒/代价高光/环境杀。每场≥1个，绑定角色情感

## Step 2: 分镜脚本

```
# | 机位 | 时长 | 内容 | 字数 | 节奏
1 | 远景 | 3s | 全战场 | 100-150 | 慢
2 | 中景 | 2s | 对峙/试探 | 80-120 | 中
3 | 快切 | 0.3s×N | 密集战斗 | ≤15字/句 | 快
4 | 慢镜头 | 5s | 关键击 | 200-300 | 极慢
5 | 特写 | 1s | 微表情 | 50-80 | 定格
```
段落长度 = 时间流速

## Step 3: 写正文

`skill_loader("novel-battle", "engine", "action")` 动作链5拍
强制规则：POV锁定 / 动作-反馈链 / 动词>形容词 / 辅助描写≤10字 / 五感反馈 / 实时代价 / 20%细节法则

战后同步：`character_update(status)` + `world_upsert`

## Step 4: 八维度审计

分镜完整性 / POV一致性 / 动作-反馈链 / 异兽差异化 / 代价系统 / 燃点 / 节奏 / 精准动词
评分 A(≥90)/B(≥80)/C(≥70)/D(<70)。C以下必须修改。

</supporting-info>
