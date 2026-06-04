# novel-distill R4 审计报告

## 5维评分

| 维度 | BEFORE | AFTER | Δ |
|------|--------|-------|---|
| D1 Frontmatter (10) | 10 | 10 | 0 |
| D2 工作流 (20) | 17 | 18 | +1 |
| D3 边界/安全 (15) | 12 | 14 | +2 |
| D4 指令精度 (20) | 17 | 19 | +2 |
| D5 实测效果 (35) | 28 | 30 | +2 |
| **总分** | **84** | **91** | **+7** |

## 10项审计

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | Framing | PASS | Lines 52-57 跨项目通用适配问题域定义清晰 |
| 2 | Literals | PASS | MCP tool names、路径均正确 |
| 3 | Script bloat | PASS | 新增元素表为声明式映射表，非脚本 |
| 4 | Untraceable imperative | PASS | 校验链每步可追踪；dimension-diff 表每字段有定义 |
| 5 | Shape-bake | PASS | 新增 JSON schema 为开放式结构 |
| 6 | Coverage | WARN | Step 3.2 空段落继承自 BEFORE |
| 7 | X-ref | PASS | skill_loader 名称与 Skill Map 一致 |
| 8 | Under-abstraction | PASS | 校验链和批量写入逻辑独立，无重复 |
| 9 | Silent-bypass | PASS | 校验链标注"写入前强制"，partial_quality 向用户报告 |
| 10 | Overfit | PASS | 无硬编码项目名；具名替换示例均为教学反例 |

## FM-PP 回归

| PP# | 结果 | 证据 |
|-----|------|------|
| PP-14 | PASS | Lines 442-443 主 agent 直写 |
| PP-15 | WARN | Line 577 top_k=50 与质量规则 ≤10 字面矛盾（文件输出场景需拉全量） |
| PP-16 | PASS | Lines 450-458 borrowable_summary 去重 |

## R5.1 模型合规

SKILL.md 为编排指令不含 Agent() 调用，调度参数 general-purpose/sonnet 合规。

## 问题清单

| # | 严重程度 | 描述 |
|---|---------|------|
| 1 | WARN | Step 3.2 "下游消费指引" 为空段落（继承） |
| 2 | WARN | top_k=50 与质量规则 ≤10 需例外说明 |
| 3 | INFO | 维度差异化 schema 增加子 agent 填写复杂度 |

## 结论: PASS (FAIL=0, WARN=2, INFO=1)
