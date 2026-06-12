---
name: novel-distill
description: >
  参考作品蒸馏引擎 v6.0.0。cangjie-skill 借鉴：V1V2V3三重质量门 + rejected审计轨迹 + trigger_signals语言信号 + 检索精度回归 + Zettelkasten关系图。
  批露式架构：编排器调度6维度子agent，规范化+校验+质量门三层后处理。
  三通道检索：ctx_index + DB向量 + keyword。
  触发词：蒸馏XX/分析小说/拆解小说/蒸馏参考/导入蒸馏/深化蒸馏
allowed-tools:
  - mcp__novel-db__*
  - mcp__novel-db__skill_loader
  - mcp__plugin_context-mode_context-mode__ctx_index
  - mcp__plugin_context-mode_context-mode__ctx_search
  - mcp__plugin_context-mode_context-mode__ctx_execute_file
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
version: "6.0.0"
---

# 参考作品蒸馏引擎 v6.0.0

## 核心概念

**`_参考库`**：novel-db 特殊小说名，存储所有参考作品蒸馏数据，全局共享。

**项目方向感知**：Phase 0 检测 CLAUDE.md 活跃项目品类，borrowable 含 `project_relevance` 字段。详见 `references/type-detection.md`。

**批露式架构**：6维度各有独立 agent 模块（`agents/dim-{dim}.md`），prompt 模板见 `references/agent-prompt.md`。

**三层后处理（v6.0 新增 V1V2V3 质量门）**：
- L1 规范化：`scripts/normalize-distill.py` — schema 字段修复
- L2 校验：`scripts/validate-distill.py` — schema 完整性 + V1V2V3 内容质量
- L3 质量门：V1跨域/V2预测力/V3独特性 — 失败项移入 `rejected/`，不进 DB

**Trigger Signals（v6.0 新增）**：每条 borrowable 强制标注"用户写作时说什么话应命中"，提升检索精度。

**Zettelkasten 关系图（v6.0 新增）**：borrowable 间三类关系（composes-with/contrasts-with/depends-on），Phase 3 生成 INDEX.md。

**文件管理**：
- 子agent 输出：`novels/_参考库/{作品名}/.distill-tmp/`（含 `rejected/` 子目录）
- 最终归档：`novels/_参考库/{作品名}/` 单层目录
- 校验脚本：`scripts/validate-distill.py`（Phase 2b.5）
- 检索回归：`scripts/retrieval-test.py`（Phase 3.5，对高优 borrowable 跑诱饵测试）

**中性化输出**：source_context / replacement_guide 禁止原作术语和具名替换。审计示例见 `references/agent-prompt.md`。

## 核心概念

**`_参考库`**：novel-db 特殊小说名，存储所有参考作品蒸馏数据，全局共享。

**项目方向感知**：Phase 0 检测 CLAUDE.md 活跃项目品类，borrowable 含 `project_relevance` 字段。详见 `references/type-detection.md`。

**批露式架构**：6维度各有独立 agent 模块（`agents/dim-{dim}.md`），prompt 模板见 `references/agent-prompt.md`。

**文件管理**（v5.0 重构）：
- 子agent 输出：`novels/_参考库/{作品名}/.distill-tmp/`（项目内持久化，Phase 3 保留供深化）
- 最终归档：`novels/_参考库/{作品名}/` 单层目录
- 校验脚本：`scripts/validate-distill.py`（Phase 2b 后处理）

**中性化输出**：source_context / replacement_guide 禁止原作术语和具名替换。审计示例见 `references/agent-prompt.md`。

## 执行流程

### Phase 0：输入确认 + 项目方向检测

1. 获取文件路径 → `ls` / `head` / `wc` 验证
2. 文件统计：行数 + 章节估计
3. 类型识别：前200行关键词匹配（表见 `references/type-detection.md`）
4. 项目方向检测：读 CLAUDE.md Active Project → 提取品类标签
5. 维度优先级 + project_relevance 评分（锚点见 `references/type-detection.md`）
6. 用户确认蒸馏计划

### Phase 1：粗提取 + 作品画像

1. 分段读取（500-800行/段，50行重叠），识别卷/章结构
2. 逐卷摘要（限200字）：事件/人物/设定/基调
3. 维度信号密度 + 项目相关度评分
4. 写入 DB：`write_to_storage("_参考库", ...)`（降级链：world_upsert → Write 文件 → Write tmp）

### Phase 1.5：已有数据导入

触发：Phase 1 后自动 / 用户说"导入 xxx.json"。扫描 `distill/*.json` → `distill(action="import")`。输出菜单：[A] 深化 / [B] 新维度 / [C] 报告。

### Phase 2：精准蒸馏

#### 2a：定位

根据维度+优先级+项目相关度生成蒸馏计划 → 用户确认。

#### 2b：子agent并行蒸馏

编排器加载 `references/agent-prompt.md` 模板 + `agents/dim-{dim}.md`，组装 prompt。

**维度模块**：`ls agents/dim-*.md` 验证（characters 复数，其余单数）。

| 维度 | 模块 | 元 skill |
|------|------|---------|
| world | dim-world | novel-setup/worldbuilding |
| ability | dim-ability | abilitycraft/ability-design |
| characters | dim-characters | novel-character/character-design |
| narrative | dim-narrative | story-architecture/narrative |
| rhythm | dim-rhythm | novel-plan/rhythm |
| highlight | dim-highlight | — |

**调度**：1维度→主agent直执（仍 Write 到 `{work_dir}/`） / 2-3→并行sonnet / 4-6→分批(每批3)sonnet。

**并行约束**：每agent限读3000行，必须用 **Write 工具**写文件到 `{work_dir}/{dim}.json`，失败→主agent串行重试。

#### 2b.4：输出规范化（v5.1 新增）

子agent 完成写入后，**立即运行规范化脚本**修复常见 schema 偏差：

```bash
python3 scripts/normalize-distill.py {work_dir}
```

自动修复项：
- 键名修正：`borrowables` → `borrowable`
- 结构包裹：裸数组 → `{dimension, data, borrowable, metadata}`
- JSON 修复：unquoted strings、trailing commas
- 字段补全：缺失的 `description`/`example`/`source_chapters`/`applicability`/`applicable_genres`/`project_relevance`
- **v6.0 新增**：`trigger_signals` 自动提取（从 description/name 抽取候选，标记 `_auto_extracted`）
- **v6.0 新增**：`quality` 默认结构（V1V2V3 全部 `passed=None` + `_note: NEEDS_MANUAL_REVIEW`）
- **v6.0 新增**：`related` 默认空数组
- 类型转换：`adaptation_map` dict→array、`elements` string→array

**规范化后立即运行校验**，若仍有错误→返回子agent修复。

#### 2b.5：脚本校验（v6.0 含 V1V2V3 质量门）

```bash
python3 scripts/validate-distill.py {work_dir}
```

校验内容：
- JSON 格式 / 必填字段（含 `trigger_signals` + `quality`）
- source_context ≥20字 / name ≤10字 / example ≤200字
- 中性化关键词扫描 / project_relevance 结构
- **V1 跨域**：`quality.v1_cross_domain.passed=true` 时 evidence 必须 ≥2 条
- **V2 预测力**：`passed=true` 时必须有 `novel_question` + `derived_answer`
- **V3 独特性**：`passed=true` 时必须有 `why_not_common`；自动检测常识模式（黑名单）→ 命中即 error
- **trigger_signals**：3-5条，非空，禁抽象描述
- **V1V2V3 任一 `passed=false`**：error（应移入 rejected/）

**校验不通过→分流：**
- schema 错误（缺字段/格式）→ 返回子agent修复后重跑
- V1V2V3 不通过 → 进入 Phase 2b.6 rejected 归档，不返回子agent

#### 2b.6：V1V2V3 失败分流 + Rejected 归档（v6.0 新增）

校验中标记 V1V2V3 失败的 borrowable，**不丢弃**，移入审计轨迹：

```python
# 主 agent 在 validate 输出后执行：
FOR dim IN validated_dims:
    FOR b IN borrowables[dim]:
        IF any(v.failed for v in b.quality):
            MOVE b TO {work_dir}/rejected/{dim}.json
            RECORD b.failed_at + reason + salvage_hint
```

输出：`{work_dir}/rejected/{dim}.json`，结构见 `references/agent-prompt.md`。

**主 agent 报告**："本作品 V1V2V3 淘汰 N 条候选（V1:x / V2:y / V3:z），已归档至 rejected/ 供后续捞回。"

#### 2b.7：文件验证（v5.0 → v6.0 编号调整）

子agent 完成后，**不依赖通知时序**，直接验证文件存在：

```
FOR dim IN 已调度维度:
    IF NOT exists("{work_dir}/{dim}.json"):
        → 串行重试该维度（最多1次）
        → 仍失败 → 标记该维度 partial，继续其他维度
    ELSE:
        → 校验通过，继续
```

### Phase 2.5：递进深化

触发：borrowable < 5 / partial > 50% / 用户说"深化 {作品} {维度}"。前置：DB 已有该维度数据。最多2轮，每轮 ≤20K token，无增量→标记"ineffective"。

**v6.0 新增**：深化时优先扫描 `rejected/{dim}.json`，对原 V1V2V3 失败项重新评估（补充 evidence / 重写 description 通过 V3），捞回成功项移回主 borrowable。

### Phase 2c：borrowable 存储

```
distill(action="batch_write", work_name, borrowables_json)
→ 校验 + quality标记 + 批量INSERT/UPDATE
```

维度 data 只存 summary，完整 borrowable 在 ref_borrowable。验证：`search(action="vector", query_text="{作品名}", top_k=3)`。

### Phase 3：报告 + 归档 + Zettelkasten

1. `distill(action="report", work_name)` → Write 蒸馏报告 + ctx_index 索引
2. 按维度 Write `borrowable-{dim}.md`
3. **v6.0 新增 Zettelkasten**：扫描所有 borrowable 的 `related` 字段 → 生成 `INDEX.md`（含 mermaid 关系图 + 推荐组合调用顺序）。模板见 `references/index-template.md`
4. **保留** `.distill-tmp/` 目录（含 `rejected/`，供后续深化蒸馏复用，不删除）
5. 清理项目根旧格式文件（`tmp_distill_*.txt`）→ 需用户确认
6. `sync(action="db_to_files", novel_name="_参考库", data_type="world")`
7. 更新 CLAUDE.md 参考作品区

输出结构：
```
novels/_参考库/
├── {作品名}/
│   ├── 蒸馏报告.md
│   ├── INDEX.md                       ← v6.0 新增：Zettelkasten 关系图
│   ├── .ctx-index.md
│   ├── borrowable-{维度}.md
│   ├── .distill-tmp/
│   │   ├── {dim}.json                 ← 含 trigger_signals + quality + related
│   │   └── rejected/{dim}.json        ← v6.0 新增：淘汰候选审计轨迹
│   └── distill/{dim}.json             ← JSON fallback
```

### Phase 3.5：检索精度回归（v6.0 新增）

对 `project_relevance.{active_project}.score >= 4` 的高优 borrowable，跑诱饵测试：

```bash
python3 scripts/retrieval-test.py {work_name} [--active-project {project}]
```

测试三类用例（来自 `evals/retrieval-cases.json`）：
- `should_trigger`：用户写作时说什么话应命中该 borrowable
- `should_not_trigger`（诱饵）：看似相关但实际不该命中
- `edge_case`：边界模糊场景

通过标准：`should_trigger >= 80%` AND `should_not_trigger >= 100%`（诱饵容错为 0）。未通过 → 修 `trigger_signals` 字段而非测试用例（除非用例本身设计错）。

**本 Phase 可选**：默认跳过，用户说"跑检索回归"或 `project_relevance=high` 的 borrowable 数 > 10 时强制执行。

## 检索协议

```
L1: ctx_search(queries=["{作品名} {需求}"], source="ref-patterns-{作品名}")
L2: search(action="vector", novel_name="_参考库", query_text="{需求}")
L3: search(action="keyword", novel_name="_参考库", keyword="{关键词}", top_k=10)
L4: 空结果 → "该模式尚未蒸馏，是否现在蒸馏？"
```

partial 降级：[A] 手动适配 / [B] 重新蒸馏 / [C] 灵感参考。

adaptation_map 使用：先读 source_context → 再看 elements → 逐项 keep→replace → 禁止 original 具名替换。

## 大文件策略

| 大小 | 策略 |
|------|------|
| < 2000 行 | 一次读取 |
| 2000-10000 行 | 分段（800行/段，50行重叠） |
| > 10000 行 | Phase 1 读首尾+卷首章，Phase 2 按维度精准读取 |

## 约束（15条，v6.0 新增 3 条）

1. **不编造**：只提取文本明确内容；Write 数据来源必须是 DB 查询
2. **中性化**：source_context/elements/adaptation_map 禁止原作术语和具名替换
3. **去重存储**：dim 模块 schema 完整字段保留在 `.distill-tmp/{dim}.json`，DB ref_* 的 data 字段只存 summary
4. **文件输出用 Write**：子agent 输出 JSON 用 Write 工具；ctx_execute 仅用于分析处理（stdout 会被索引），其 sandbox 内文件写入不持久化到 host
5. **top_k 必带**：keyword search 必须 top_k ≤ 10
6. **项目感知**：borrowable 含 project_relevance（检索标签，不改通用性）
7. **batch_write 走 MCP**：主agent 调 distill(batch_write)，不用子agent
8. **Phase 1 前置**：不跳 Phase 1 直接 Phase 2
9. **命名一致**：characters 复数，其余单数，启动前 ls 验证
10. **不存原文**：example 限 ≤200 字
11. **并行隔离**：子agent 不共享未校验中间结果
12. **校验必过**：validate-distill.py 错误→返回子agent修复→重跑（最多3次），仍失败标记 partial
13. **规范化先行**：子agent写入后必须先 normalize-distill.py 再 validate-distill.py，禁止跳过规范化
14. **V1V2V3 强制（v6.0）**：每条 borrowable 必须有 `quality` 字段；V1V2V3 任一 `passed=false` → 必须移入 `rejected/{dim}.json`，不留在主 borrowable；淘汰候选不丢弃
15. **trigger_signals 强制（v6.0）**：每条 borrowable 必须有 3-5 条用户语言信号；normalize 自动填充的需主 agent 在 Phase 3 报告前人工校核（标记 `_auto_extracted`）
16. **Zettelkasten 节制（v6.0）**：`related` 字段不硬造关系；无真正关系的留空数组 `[]`；合理关系数约 8-15 条/10个 borrowable

## 子 Agent 编排

详见 `agents/claude-code.yaml`（v6.0 新增，遵循 skill-creator 标准）。6 维度模块仍保留 `agents/dim-{dim}.md` 作为 prompt 模板。

## 评估与回归

- `evals/quality-gate.md`：V1V2V3 三重验证 rubric（借鉴 cangjie-skill Triple Verification）
- `evals/retrieval-cases.json`：检索精度诱饵测试集（should_trigger / should_not_trigger / edge_case）
