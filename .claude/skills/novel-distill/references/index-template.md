# INDEX.md 模板（Zettelkasten 关系图）

借鉴 cangjie-skill 的 Zettelkasten 链接 + INDEX.md。Phase 3 时由主 agent 扫描所有 borrowable 的 `related` 字段生成。

## 模板

```markdown
# {作品名} — 借鉴模式地图

## 基本信息

- **作者**：{author}
- **年份**：{year}
- **一句话主旨**：{one_line_thesis}
- **蒸馏时间**：{distilled_at}
- **borrowable 总数**：{total}（world: {n1} / ability: {n2} / characters: {n3} / narrative: {n4} / rhythm: {n5} / highlight: {n6}）
- **淘汰候选**：{rejected_count}（见 `.distill-tmp/rejected/`）

## 按维度分组的 borrowable

### 世界观（world）
- [{name}]({anchor}) — {description} [相关度: ★{score}]
- ...

### 能力体系（ability）
- ...

[其他维度]

## 关系图（Mermaid）

​```mermaid
graph LR
  A[暖色弧] -->|composes-with| B[暗线钩子]
  A -->|contrasts-with| C[冷色弧]
  B -->|depends-on| A
  D[小胜利] -->|depends-on| A
  E[不可逆死亡] -->|composes-with| C
​```

## 推荐组合调用

### 写"暖色弧"时
1. `暖色弧构造`（主）
2. `暗线钩子埋设`（composes-with）
3. `小胜利设计`（depends-on）

### 写"冷色弧"时
1. `冷色弧推进`（主）
2. `不可逆死亡/代价感`（composes-with）
3. `暗线钩子兑现`（来自上一轮暖色弧）

## 关系统计

| 关系类型 | 数量 |
|---------|------|
| composes-with | {n} |
| contrasts-with | {n} |
| depends-on | {n} |
| **总计** | {total_relations} |

合理范围：每 10 个 borrowable 约 8-15 条关系。<5 说明拆得太独立，>25 说明在硬凑。

## 检索入口

- L1 ctx_search: `ctx_search(queries=["{作品名} {需求}"], source="ref-patterns-{作品名}")`
- L2 vector: `search(action="vector", novel_name="_参考库", query_text="{需求}")`
- L3 keyword: `search(action="keyword", novel_name="_参考库", keyword="{关键词}", top_k=10)`
```

## 生成规则

1. 扫描所有 `.distill-tmp/{dim}.json` 的 `borrowable[].related` 字段
2. 收集所有 `slug + relation` 对，去重
3. 按 relation 类型分组统计
4. 生成 mermaid 图（节点用 borrowable.name，边用 relation）
5. 推荐组合调用：从 `composes-with` 链推导
