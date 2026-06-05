---
name: novel-distill
description: >
  参考作品蒸馏引擎 v5.0.0。项目方向感知 + 脚本校验 + 持久化中间产物。
  批露式架构：编排器调度6维度子agent，脚本化后处理校验。
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
version: "5.0.0"
---

# 参考作品蒸馏引擎 v5.0.0

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

#### 2b.5：脚本校验（v5.0 新增）

```bash
python3 scripts/validate-distill.py {work_dir}
```

校验内容：JSON 格式 / 必填字段 / source_context ≥20字 / name ≤10字 / example ≤200字 / 中性化关键词扫描 / project_relevance 结构。**校验不通过→返回子agent修复后重跑校验。**

#### 2b.6：文件验证（v5.0 新增）

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

### Phase 2c：borrowable 存储

```
distill(action="batch_write", work_name, borrowables_json)
→ 校验 + quality标记 + 批量INSERT/UPDATE
```

维度 data 只存 summary，完整 borrowable 在 ref_borrowable。验证：`search(action="vector", query_text="{作品名}", top_k=3)`。

### Phase 3：报告 + 归档

1. `distill(action="report", work_name)` → Write 蒸馏报告 + ctx_index 索引
2. 按维度 Write `borrowable-{dim}.md`
3. **保留** `.distill-tmp/` 目录（供后续深化蒸馏复用，不删除）
4. 清理项目根旧格式文件（`tmp_distill_*.txt`）→ 需用户确认
5. `sync(action="db_to_files", novel_name="_参考库", data_type="world")`
6. 更新 CLAUDE.md 参考作品区

输出结构：
```
novels/_参考库/
├── {作品名}/
│   ├── 蒸馏报告.md
│   ├── .ctx-index.md
│   ├── borrowable-{维度}.md
│   ├── .distill-tmp/{dim}.json   ← 持久化中间产物（脚本校验 + 深化复用）
│   └── distill/{dim}.json        ← JSON fallback
```

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

## 约束（12条）

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
