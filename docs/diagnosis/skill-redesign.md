# Skill 重新设计方案

> 原则：每个 skill 只做一件事，用户自己选择下一步做什么。
> 目标：每个 skill < 80 行，不自动串联，不教 MCP 怎么干活。
> 约束来源：从小说数据加载，不硬编码。层级覆盖：系统 < 品类 < 小说 < 卷 < 章。

---

## 约束层级覆盖机制

不同小说风格不同，约束从小说自己的数据注入，不是所有小说用同一套规则。

```
系统默认（writing-constraints.md，通用反AI/标点/结构）
  ↑ 被覆盖
品类模板（writing_rules category='genre'，玄幻/末世/科幻各有不同）
  ↑ 被覆盖
小说专属（world_settings 氛围DNA + writing_rules 小说级规则）
  ↑ 被覆盖
卷级约束（volume.notes / writing_priorities，某卷特别暗/特别燃）
  ↑ 被覆盖
章级约束（chapter outline 中的基调字段，这章是回忆/战斗/日常）
```

| 层级 | 数据源 | 谁创建 | 举例 |
|------|--------|--------|------|
| 系统默认 | `writing-constraints.md` | 项目内置 | 禁AI味词、标点多样性 |
| 品类模板 | `writing_rules(category='genre')` | novel-setup 时根据品类自动注入 | 玄幻的升级节奏 vs 末世的生存压力 |
| 小说专属 | `world_settings(氛围DNA)` + `writing_rules` | novel-setup 时用户确认 | 禁忌清单、词汇色彩、感官锚点 |
| 卷级 | `volume_update(notes)` | novel-plan 时设定 | "这卷紧迫——妹妹要死了" |
| 章级 | `chapter_plan(outline)` 中的基调字段 | novel-plan 时设定 | "这章日常" / "这章高潮" |

**skill 不硬编码任何约束。** 约束全部从 DB 加载，`get_chapter_context` / `world_query` 自动按层级聚合。高层覆盖低层，skill 只读最终结果。

---

## 总览

| Skill | 触发词 | 做什么 |
|-------|--------|--------|
| novel-setup | 新建小说/建世界观 | 项目创建 + 世界氛围 + 世界观维度 |
| novel-character | 设计人物/加人物 | 角色档案 + 关系 |
| novel-plan | 规划大纲/设计卷 | 全书框架或卷级大纲 |
| novel-write | 写第N章/继续写 | 单章正文生成 |
| novel-review | 审阅/检查/诊断 | 质量审查 |
| novel-fix | 修复/润色/改文 | 文本修订 |

**删除**：novel-writer（路由器不再需要）、novel-skill-creator（元技能保留但非核心）、novel-ability-designer（已废弃）。

**合并**：planner + planner-volume → novel-plan。qa + creative-analyze → novel-review。

---

## novel-setup

```markdown
---
name: novel-setup
description: 项目创建与世界观构建
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep, Bash
---

# 项目创建与世界观构建

## 触发
用户说"新建小说""建世界观""加设定""加物品"。

## 项目创建
1. `novel_create(novel_name)` 建项目
2. 逐问深挖（画面/主角/情绪/对立面/独特规则，每次只问一个）
3. 用户确认决策卡 → `novel_update(status="worldbuilding")`

## 世界氛围 DNA
决策卡确认后，逐步确认氛围（不一次性生成）：
1. 问用户：你的世界什么感觉？（时代/温度/参考作品）
2. 提取氛围标签 → 用户确认 → `world_upsert(category='core_setting', name='世界氛围DNA')`
3. 生成 1-2 个感官锚点 → 用户确认 → 更新 DB
4. 写 1 个参考片段（100-200字）→ 用户确认 → 再写下一个（共 2-3 个）
5. 生成禁忌清单 + 词汇色彩 → 用户确认 → 更新 DB
6. 汇总写入 `novels/{小说名}/设定/写作/world-atmosphere.md`

## 世界观维度
逐维度展开，每维度用户确认后才继续：
种族 → 势力 → 地理 → 能力 → 经济 → 日常 → 历史 → 物品

每维度：`world_upsert` → 用户确认 → 下一维度。

## 交叉验证
全部维度完成后跑 6 项验证（锚点/稀缺/涟漪/价值/术语/氛围）。

## 完成后
问用户：设计人物 / 规划大纲 / 其他。
```

~40 行。vs 原来 237 行。

---

## novel-character

```markdown
---
name: novel-character
description: 角色设计与修改
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep
---

# 角色设计与修改

## 触发
用户说"设计人物""加人物""改人物""人物卡"。

## 新建角色
1. `world_query` 加载世界观（种族/势力/能力）
2. 与用户确认：姓名/角色/背景/性格/目标
3. 蒸馏 7 维度（决策引擎/声音指纹/行为模式等），逐步确认
4. 外观描写 + 对话风格
5. `character_create` + 关系创建 `relation_create`
6. 用户确认 → `sync_db_to_files`

## 修改角色
1. `character_detail` 读取现有档案
2. 与用户确认修改范围
3. `character_update` 更新
4. 用户确认 → `sync_db_to_files`

## 约束
- 从 `world_settings` 和 `writing_rules` 加载当前小说的约束（氛围DNA/禁忌清单/术语映射等）
- 高层覆盖低层，不硬编码

## 完成后
问用户：继续加人物 / 规划大纲 / 其他。
```

~35 行。vs 原来 135 行。

---

## novel-plan

```markdown
---
name: novel-plan
description: 大纲规划（全书或单卷）
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep, Bash, Agent, Task
---

# 大纲规划

## 触发
用户说"规划大纲""设计卷""全书框架""章节规划"。

## 前置检查
- 项目已创建（novel-setup 完成）
- 世界观 ≥ 3 维度
- 角色 ≥ 2 个
- 不满足 → 提示用户先补齐，不自动跳转

## 模式选择（问用户）
1. **全书框架** — 每卷"做什么"，不设计具体事件
2. **单卷大纲** — 某卷每章"怎么做"

用户选哪个做哪个，不自动串联。

## 全书框架
1. 加载：`world_query` + `character_list` + `foreshadow_list` + 氛围 DNA
2. 设计框架（起承转合/卷功能/因果链/主线暗线）
3. 用户确认 → `volume_create` / `volume_update` + `foreshadow_plant`
4. 写入 `novels/{小说名}/设定/大纲/`

## 单卷大纲
1. 加载：`volume_get` + 全书框架 + 角色蒸馏卡 + 未回收伏笔 + 氛围 DNA
2. 设计事件架构（因果链/人物弧光/悬念锚点）→ 用户确认
3. 设计逐章大纲（场景/伏笔/声音适配）→ 用户确认
4. 三视角审查（读者/作者/人物并行）→ 修复 P0
5. `chapter_plan` + `scene_create` + `foreshadow_plant` + 新实体入库
6. 写入 `novels/{小说名}/设定/大纲/V{N}-{卷名}.md`

## 约束
- 从 `world_settings` / `writing_rules` / 氛围DNA 加载约束
- 每章 ≥ 3 个可辨识事件
- 因果链不可断
- 巧合计 ≤ 1 次/卷

## 完成后
问用户：设计其他卷 / 开始写正文 / 其他。
```

~50 行。vs 原来 planner 136 行 + planner-volume 760 行 = 896 行。

---

## novel-write

```markdown
---
name: novel-write
description: 单章正文生成
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep, Bash
---

# 单章正文生成

## 触发
用户说"写第N章""继续写"。

## 前置检查
- 卷级大纲存在（该章在 novel-plan 中已规划）
- 不满足 → 提示用户先做大纲

## 流程
1. `get_chapter_context(novel_name, chapter_number)` 获取上下文包
2. 基于上下文做创意决策（场面/因果链/角色弧线/伏笔操作/新实体）
3. 用户确认创意蓝图
4. `resolve_engines(场景类型)` 获取引擎
5. 逐场面生成正文（遵守 writing_rules 表所有规则）
6. `validate_chapter(正文)` 校验 → 有违规必须修复
7. 通过 → `writing_finish(...)` 存盘 + 角色快照 + 关系快照
8. 正文写入 `novels/{小说名}/正文/第{NNN}章-{标题}.md`

## 约束
- 从 `get_chapter_context` 返回的约束层级加载（系统→品类→小说→卷→章，高层覆盖低层）
- 字数 ≥ 3000（不含标点）

## 完成后
问用户：写下一章 / 审阅 / 其他。
```

~30 行。vs 原来 427 行。

---

## novel-review

```markdown
---
name: novel-review
description: 质量审查与诊断
allowed-tools: mcp__novel-db__*, Read, Glob, Grep, Bash
---

# 质量审查与诊断

## 触发
用户说"审阅""检查""诊断""OOC""创意分析"。

## 模式选择（问用户）
1. **大纲审查** — 审卷级大纲的因果链/人物弧光/伏笔
2. **正文审查** — 审章节文本（三视角：读者/作者/人物）
3. **设定审查** — 审世界观一致性
4. **健康诊断** — 伏笔积压/配角活跃/升级节奏/卷完成度
5. **创意评估** — 惊喜度/独特性/情感冲击（找"不够好"而非"有错"）

用户选哪个做哪个。

## 大纲审查
加载大纲 + 角色蒸馏卡 → 逐项检查 → 出审计报告

## 正文审查
加载章节文本 + 角色档案 + 世界观 → 三视角并行审查 → 分级问题（P0/P1/P2）

## 健康诊断
`health_check(novel_name)` → 出诊断报告

## 输出
审计报告写入 `novels/{小说名}/审阅报告/`

## 完成后
问用户：修复问题 / 继续写 / 其他。
```

~30 行。vs 原来 qa 287 行 + creative-analyze 165 行 = 452 行。

---

## novel-fix

```markdown
---
name: novel-fix
description: 文本修复与润色
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep, Bash
---

# 文本修复与润色

## 触发
用户说"修复""润色""改文""去重"。

## 模式
1. **修复** — 针对审阅报告中的 P0/P1 问题逐项修复
2. **润色** — 提升文笔质量（不改变情节）
3. **术语修复** — 批量替换违规术语

## 执行
1. 定位问题段落
2. 修复
3. `validate_chapter` 重新校验
4. 用户确认 → 更新文件 + DB

## 完成后
问用户：继续修复 / 写正文 / 其他。
```

~25 行。vs 原来 168 行。

---

## 收益对比

| 指标 | 现状 | 方案 | 变化 |
|------|------|------|------|
| skill 数量 | 11 | 6 | -45% |
| SKILL.md 总行数 | 2593 | ~210 | **-92%** |
| SKILL.md 总体积 | 117KB | ~8KB | **-93%** |
| 单次触发 token | ~94K | ~5K | **-95%** |
| 自动串联 | 全流程自动推进 | 每步问用户 | 用户掌控 |
| 规则存储 | 散落 skill 里 | DB writing_rules | 单源维护 |
| 引擎加载 | skill 硬编码清单 | resolve_engines MCP | 自动匹配 |
| DB MCP 使用率 | 低 | 高（主数据通道） | 质变 |

---

## 不做的事

| 不做 | 理由 |
|------|------|
| 不在 skill 里写 DB 保存伪代码 | MCP 工具自己知道怎么存 |
| 不在 skill 里列引擎加载清单 | resolve_engines 自动匹配 |
| 不在 skill 里写检查点显示模板 | 模型自己组织输出 |
| 不自动跳转下一步 | 用户自己选 |
| 不重复写通用规则 | 规则在 DB writing_rules，skill 只写独有约束 |
