# Token预算估算与引擎加载

## Token预算估算

```python
TOKEN_BUDGET_LIMIT = 80000  # 留余量给 Agent 产出 + 对话

estimated_tokens = (
    5 * 2000 +   # 结构引擎（causality + three-perspective + 3个perspective-agent）
    4 * 1500 +   # 术语规范（lorecraft core-principles + term-map + quickref + world-element-registry）
    5 * 1000 +   # 基础数据（novel_get + world_query + character_list + foreshadow_list）
    15 * 200     # 已有卷信息（15卷 × volume_get notes约200 tokens）
)
# estimated_tokens ≈ 24000（正常情况不会超限）
# v1.4时: 读15卷大纲 ~150K tokens → v1.5: volume_get notes ~3K tokens，节省约120K

if estimated_tokens > TOKEN_BUDGET_LIMIT:
    apply_tiered_loading = True
else:
    apply_tiered_loading = False
```

## 分层加载策略

| 层级 | 内容 | 加载时机 |
|------|------|---------|
| Tier 1（始终加载） | lorecraft term-map + quickref + world-element-registry | Step 0 |
| Tier 2（按步骤加载） | Step 1/2 → causality + three-perspective；Step 5 → 3个perspective-agent | 对应Step启动时 |
| Tier 3（按需加载） | lorecraft core-principles 全文（紧张时只加载前20行：原则+关键约束） | 上下文紧张时 |

> **引擎精简版机制**：如果上下文仍然紧张，Agent 可只加载引擎的前 20 行（原则+关键约束），跳过示例和详细说明。核心规则集中在文件开头，精简版不影响约束效果。

## 引擎加载执行

```python
# Step 1/2 需要：
skill_loader("novel-planner", "engine", "causality")
skill_loader("novel-planner", "engine", "three-perspective")
# Step 5 需要：
skill_loader("novel-planner", "engine", "reader-perspective-agent")
skill_loader("novel-planner", "engine", "author-perspective-agent")
skill_loader("novel-planner", "engine", "character-perspective-agent")

# 🔒 术语规范（全程强制加载——所有Agent生成前必读、生成后必检）：
Read(".claude/skills/lorecraft/references/core-principles.md")
Read(".claude/skills/lorecraft/references/term-map.md")
Read(".claude/skills/lorecraft/references/quickref.md")
Read(".claude/skills/engines/world-element-registry.md")
```

## 引擎加载验证

```python
loaded_engines = {
    "Step1-因果链(causality)": causality_loaded,
    "Step2-三视角(three-perspective)": three_perspective_loaded,
    "Step5-读者视角(reader-perspective)": reader_loaded,
    "Step5-作者视角(author-perspective)": author_loaded,
    "Step5-人物视角(character-perspective)": character_loaded,
    "术语核心原则(lorecraft-core)": lorecraft_loaded,
    "术语映射(term-map)": term_map_loaded,
    "术语速查(quickref)": quickref_loaded,
    "世界元素注册表(world-element-registry)": world_element_registry_loaded,
}

failed = [k for k, v in loaded_engines.items() if not v]
if failed:
    print(f"以下资源加载不完整：{failed}")
    print("请缩短其他内容或分批处理。")
    return  # 阻断，不启动Agent
else:
    print(f"✅ 全部 {len(loaded_engines)} 个引擎/规范加载成功")
```

**验证的作用**：引擎是后续所有步骤的约束条件，缺失引擎意味着 Agent 将在无约束状态下运行，产出可能违反因果逻辑、术语规范或三视角标准。修复成本远高于重新加载。如果上下文不足，编排器应提示用户并等待调整，而非静默跳过。
