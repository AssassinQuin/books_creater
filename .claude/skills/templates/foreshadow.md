# 伏笔模板

> 权威源：DB `foreshadows` 表。文件为可读副本。

## DB 字段映射

| MD字段 | DB列 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| description | description | TEXT | ✅ | 伏笔描述 |
| status | status | TEXT | ✅ | planted/recalled/abandoned |
| importance | importance | TEXT | ✅ | high/medium/low |
| planted_chapter | planted_chapter_id | INT | ✅ | 埋设章节ID |
| planned_recall_chapter | planned_recall_chapter | INT | 可选 | 计划回收章节 |
| related_characters | related_characters | JSON | 可选 | 相关角色ID列表 |
| tags | tags | JSON | 可选 | 标签列表 |
| clue_type | clue_type | TEXT | 可选 | 线索类型（物证/对话/行为/环境/暗示） |
| reveal_strategy | reveal_strategy | TEXT | 可选 | 揭示策略（渐进/突然/反转/读者先知） |
| related_foreshadows | related_foreshadows | JSON | 可选 | 关联伏笔ID列表 |

---

# 回响模板（Echo）

> 权威源：DB `echoes` 表。文件为可读副本。
> 与伏笔的区别：伏笔是"先埋后收"（向前看），回响是"先发生后回声"（向后看）。

## DB 字段映射

| MD字段 | DB列 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| source_event | source_event | TEXT | ✅ | 被回溯的原始事件/人/物品/地点/梗 |
| echo_type | echo_type | TEXT | ✅ | character_habit/physical_trace/catchphrase/location_change/item/memory |
| echo_description | echo_description | TEXT | 可选 | 回响的具体写法（一句话） |
| strong_related | strong_related | INT | ✅ | 1=强相关（不受密度限制） |
| source_chapter | source_chapter_id | INT | ✅ | 原始事件发生章节ID |
| echo_chapter | echo_chapter_id | INT | ✅ | 回响出现章节ID |
| volume | volume_id | INT | 自动 | 所属卷ID（从echo_chapter自动推断） |
| tags | tags | JSON | 可选 | 标签列表 |

## 密度规则

| 类型 | 限制 | 说明 |
|------|------|------|
| 普通回响 | ≤2次/卷 | 太多会像刻意提醒读者"还记得吗？" |
| 强相关回响 | 不限 | 与当前主线强相关的梗/人/物品/地点可以更频繁 |
| 跨卷回响 | ≤1次/跨卷间隔 | 读者记忆有限，偶尔点到为止最有效 |

## 融入方式

- ✅ 融入世界呼吸：角色在日常动作中自然碰到
- ✅ 融入角色对话：他人无意中使用
- ❌ 独立段落：这是回忆杀，不是回响

## 文件格式（`设定/大纲/回响清单.md`）

```markdown
# 回响清单

## echo: {id}
- **source_event**: {被回溯的原始事件/人/物品/地点/梗}
- **echo_type**: character_habit/physical_trace/catchphrase/location_change/item/memory
- **echo_description**: {回响的具体写法}
- **strong_related**: 0/1
- **source_chapter**: Ch{N}
- **echo_chapter**: Ch{M}
- **tags**: [{标签列表}]
```

---

## 扩展机制

新增维度时：
1. 在 DB `foreshadows` 表新增列
2. 在本模板追加字段
3. 在 `foreshadow(action="plant")` MCP 工具中新增对应参数
4. 更新 `consistency_guard` 的字段映射表
