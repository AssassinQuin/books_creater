# 人物关系模板

> 权威源：DB `character_relations` 表。文件为可读副本。

## DB 字段映射

### 基础层

| MD字段 | DB列 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| from | from_character_id | INT | ✅ | 关系发起方ID |
| to | to_character_id | INT | ✅ | 关系接受方ID |
| relation_type | relation_type | TEXT | ✅ | ally/enemy/mentor/lover/family/rival/subordinate |
| description | description | TEXT | ✅ | 关系描述 |
| intensity | intensity | INT | 可选 | 强度1-10（默认5） |
| chapter_established | chapter_established | INT | 可选 | 关系建立章节 |

### 丰富数据层（JSONB字段）

### 对话调节表 (`dialogue_adjustment`)

```json
{
  "tendency": "对该人的整体说话倾向",
  "style": "句式/用词/语气变化",
  "example": "示例对话",
  "taboo": ["不会对该人说的话"],
  "unique_habits": ["只对该人才有的说话习惯"]
}
```

### 微表情词典 (`micro_expressions`)

```json
[
  {
    "context": "情绪/场景",
    "action": "具体动作（只对该人才有）",
    "meaning": "含义"
  }
]
```

### 弦外之音设计 (`subtext_design`)

```text
这段关系中的弦外之音设计原则。如：对TA的关心永远通过动作表达，不说破。
```

---

## 文件格式（`设定/人物/{名}.md` 中的关系部分，或 `设定/角色总览.md`）

```markdown
## 关系
- **relation_type**: {值}
- **from**: {角色名}
- **to**: {角色名}
- **description**: {值}
- **intensity**: {值}
- **dialogue_adjustment**: {JSON}
- **micro_expressions**: {JSON数组}
- **subtext_design**: {TEXT}
```

---

## 扩展机制

新增维度时：
1. 在 DB `character_relations` 表新增 JSONB 列
2. 在本模板追加新节
3. 在 `relation_create` / `relation_update` MCP 工具中新增对应参数
4. 更新 `consistency_guard` 的字段映射表
