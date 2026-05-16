# 加载引擎 engine-loading.md

> 统一的上下文加载协议。所有写作类skill通用。核心目标：省token+提高正文准确性。

## 加载时机

所有写作类skill在生成正文/规划大纲前执行加载。

---

## 加载协议（按优先级）

### Tier 1: 必须加载（缺则报错）

```yaml
1. 卷级大纲:
   工具: volume_get_by_number(novel_name="这次不一样了", number={volume_number})
   提取: 卷标题 + main_plotlines + notes
   目的: 知道当前卷在写什么

2. 章节大纲:
   工具: get_chapter_context(novel_name="这次不一样了", chapter_number)
   一次返回: 章节信息 + 卷级大纲 + 前3章摘要 + 角色深度信息 + 未回收伏笔 + 世界观 + 人物关系 + 时间线 + 质量历史 + 写作提示词
   目的: 核心上下文，一次性获取

3. 活跃人物档案:
   工具: character_get_by_name(novel_name="这次不一样了", character_name={name}) 对每个出场人物
   提取字段:
     - name, gender, appearance, personality
     - speech_style, catchphrase
     - ability_level, status(当前状态JSON)
     - goals, weaknesses
   目的: 对话/动作/描写一致性

4. 人物关系:
   工具: relation_list(novel_name="这次不一样了")
   提取: 出场人物之间的关系类型+强度
   目的: 对话语气差异化
```

### Tier 2: 按需加载（有则用，无则跳）

```yaml
5. 环境快照:
   工具: world_query(novel_name="这次不一样了", category="location", name="{本章地点}")
   提取: 空间结构 + 灵能维度 + 感官基线
   目的: 环境一致性

6. 物品档案:
   工具: world_query(novel_name="这次不一样了", category="ability"/category="economy", name="{物品名}")
   提取: 外观+触感+功能+当前状态
   目的: 物品使用一致性

7. 历史层:
   工具: world_query(novel_name="这次不一样了", category="history", name="{相关历史}")
   提取: 遗留规则+失传规则+自洽性锚点
   目的: 设定经得起推敲

8. 未回收伏笔:
   工具: foreshadow_list(novel_name="这次不一样了", status="planted")
   提取: description + planned_recall_chapter + tags
   目的: 本章是否该推进某条暗线
```

### Tier 3: 增强加载（有精力/重要章节时）

```yaml
9. 时间线:
   工具: timeline_query(novel_name="这次不一样了", from_chapter=N-3, to_chapter=N)
   提取: 近期事件序列
   目的: 防止时空矛盾

10. 维度变化:
    工具: dimension_query(novel_name="这次不一样了", from_chapter=N-3)
    提取: 近期能力/空间/经济/状态变化
    目的: 连续性追踪
```

---

## Token优化策略

### 按需提取，不全量加载
```
❌ character_get → 返回全部字段 → 全部塞进context
✅ character_get → 只提取本章需要的:
   - 本章有对话 → 提取 speech_style + catchphrase + personality
   - 本章有动作 → 提取 ability_level + status
   - 本章有外观描写 → 提取 appearance + gender
   - 不需要的字段跳过
```

### 增量更新，不全量重写
```
写完一章后:
- 只更新出场人物的状态 → character_update 只改 status 字段
- 只更新变化的环境 → world_upsert 只改变化属性
- 只新增本章的伏笔/时间线 → foreshadow_plant / timeline_add
- 不出场的角色/不变化的地点 → 不动
```

### 快照精简
```
场景快照不超过200字:
"第三区管道断裂口。灵能浓度中等。灰白结晶闪光。焦糊味。
 沈野(前方探路)、方岩(后方拖右腿)。一只灰蜥在前方15步啃食。"
→ 不是完整描写，是关键信息的速记。细节在正文中展开。
```

---

## 存储决策：DB vs 文件

### DB存储（novel-db MCP）
适合：结构化数据、需要查询检索、多skill共享、增量更新

| 数据类型 | 存储位置 | 工具 |
|----------|---------|------|
| 人物档案+状态 | character表 | character_create/update/get |
| 人物关系 | relation表 | relation_create/list |
| 世界观设定 | world表 | world_upsert/query |
| 地点快照 | world表(category="location") | world_upsert/query |
| 物品档案 | world表(category="ability/economy") | world_upsert/query |
| 历史层 | world表(category="history") | world_upsert/query |
| 伏笔 | foreshadow表 | foreshadow_plant/list/recall |
| 时间线 | timeline表 | timeline_add/query |
| 章节摘要 | chapter表 | chapter_save_summary |
| 维度变化 | dimension表 | dimension_log/query |

### 文件存储（Git）
适合：长文本、人可读、需要版本对比、频繁手动修改

| 数据类型 | 存储位置 |
|----------|---------|
| 正文 | novels/{小说名}/正文/第{NNN}章-{标题}.md |
| 卷级大纲 | novels/{小说名}/设定/大纲/ |
| 审阅报告 | novels/{小说名}/审阅报告/ |
| 角色深化文档 | novels/{小说名}/设定/角色总览.md |
| 锁定设定 | novels/{小说名}/设定/锁定设定.md |
| 写作执行规范 | novels/{小说名}/设定/写作执行规范.md |

### 原则
- **DB优先**: 如果数据需要skill自动读写 → DB
- **文件为辅**: 如果数据主要人工维护/阅读 → 文件
- **不重复存**: 同一数据只在一处存主版本，另一处用指针引用
- **增量更新**: 每次只更新变化的部分
