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

## 文件格式（`设定/大纲/伏笔清单.md`）

```markdown
# 伏笔清单

## foreshadow: {id}
- **description**: {伏笔描述}
- **status**: planted/recalled/abandoned
- **importance**: high/medium/low
- **planted_chapter**: Ch{N}
- **planned_recall_chapter**: Ch{M}
- **clue_type**: {线索类型}
- **reveal_strategy**: {揭示策略}
- **related_characters**: [{角色ID列表}]
- **related_foreshadows**: [{关联伏笔ID列表}]
- **tags**: [{标签列表}]
```

---

## 扩展机制

新增维度时：
1. 在 DB `foreshadows` 表新增列
2. 在本模板追加字段
3. 在 `foreshadow_plant` MCP 工具中新增对应参数
4. 更新 `consistency_guard` 的字段映射表
