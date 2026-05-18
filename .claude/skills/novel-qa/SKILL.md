---
name: novel-qa
description: 小说全链路质量保障。支持大纲审阅、正文审阅、设定审查、健康诊断、级联更新五种模式。触发词：审阅大纲/审阅正文/审设定/诊断/卡文/OOC/检查/改设定
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*, skill_loader
depends_on: lorecraft, engines/outline-review, engines/causality, engines/anti-ai, engines/reader-perspective-agent, engines/author-perspective-agent, engines/character-perspective-agent
lifecycle: quality
version: "1.1.0"
---

# 小说质量保障

<what-to-do>

## Step 0: 路由（意图识别）

根据用户输入分发到对应审阅流程：

| 用户输入关键词 | 目标流程 | 审阅对象 |
|--------------|---------|---------|
| "大纲"/"框架"/"卷大纲" | B3-大纲审阅 | 卷级/全书大纲文件 |
| "正文"/"最近"/"章节"/"校对" | B3-正文审阅 | 正文md文件 |
| "设定"/"OOC"/"世界观" | C4-设定审查 | DB全量设定数据 |
| "诊断"/"卡文"/"写不动"/"健康" | C2-健康诊断 | DB健康指标 |
| "改设定"/"改人物"/"级联" | C3-级联更新 | DB + 受影响章节 |

无法匹配时 → 提示用户："请选择审阅类型：①大纲 ②正文 ③设定 ④诊断 ⑤级联更新"

---

## 问题分级标准

以**读者流失风险**和**修复成本**为双轴判定。

| 级别 | 判定标准 | 处理要求 |
|------|---------|---------|
| P0-致命 | 因果链断裂/人物OOC/设定矛盾/违禁词/术语违规 | 必须修复，阻断发布 |
| P1-严重 | 伏笔未回收/节奏断层/质量波动/新术语无文化出处 | 必须修复，限1轮内 |
| P2-中等 | 描写冗余/对话平淡/爽点不足 | 应当修复，可延期 |
| P3-轻微 | 标点不均/用词重复/格式不统一 | 批量处理，不阻塞 |

---

## B3-1: 大纲审阅

```
Step 1: 加载 skill_loader("novel-qa", "engine", "outline-review")
Step 2: 10维度Agent审计（结构/起承转合/伏笔密度/人物弧光/支线检验/情绪曲线/悬念密度/世界观一致性/因果链/可读性）
Step 3: 因果链问题 → 加载 causality 引擎，自动判P0
Step 4: 🔒 评分卡 → P0/P1修复（每问题3方案+代价评估）
Step 5: 重评（最多3轮迭代）
Step 6: 输出到 novels/{NOVEL_NAME}/审阅报告/大纲审计-{date}.md
```

通过阈值：综合得分前20%-30%（A档）。超过3轮仍未通过 → 退回重新规划。

---

## B3-2: 正文审阅

### Step 1: 加载上下文

- 角色状态（`character_get` + `chapter_get_context`，novel_name=NOVEL_NAME）
- 卷级大纲（`novels/{NOVEL_NAME}/设定/大纲/V{卷号}-{卷名}.md`）
- 全书支线总图（`novels/{NOVEL_NAME}/设定/大纲/支线总图.md`）
- 世界观数据（`world_query(novel_name=NOVEL_NAME)`；空时回退读文件）
- 作者声音（`skill_loader("novel-qa", "engine", "author-voice")`）
- 🔒 术语规范（`lorecraft/references/term-map.md` — 强制加载）

### Step 2: 分组扫描（串行+并行混合）

> **核心改进**：从8+ Agent同时并行改为"基础组→深度组→交叉组"三级串行。

**第一组：基础检查**（串行，必须全部通过）
- Agent-A 人物：OOC检测 / 知识矛盾 / 说话风格 / 关系合理性
- Agent-B 逻辑：时间线连贯 / 经济一致 / 伏笔回收 / 物品逻辑
- Agent-C 术语：术语合规扫描（加载 term-map.md，标记现代科技术语偏离）

**第二组：深度审查**（并行，基于第一组结果）
- Agent-D 质量：战斗场面 / 章节结构 / 爽点分布 / NPC活跃度 / AI指纹
- Agent-E 支线：支线节点执行 / 主线交织 / 角色出场合理性
- Agent-F 三视角（3子Agent并行）：
  - Agent-F1 读者视角（`engines/reader-perspective-agent.md`）
  - Agent-F2 作者视角（`engines/author-perspective-agent.md`）
  - Agent-F3 人物视角（`engines/character-perspective-agent.md`）

**第三组：交叉检查**（编排器汇总后执行）
- 读者 vs 作者 / 读者 vs 人物 / 作者 vs 人物 冲突检测

> 如果第一组发现P0级问题（如OOC或因果链断裂），**中止第二组**，直接进入修复流程。

### Step 3: 硬约束复核

`validate_chapter(chapter_text)` — 写时自检的补充验证。

### Step 4: Smell Test

核心问题：**这章读起来像人写的，还是AI生成的？**

常见AI写作特征（应转化为更具画面感和人物特异性的表达）：
- 旁白式心理总结（"他知道/她明白"）→ 动作、微表情或对话潜台词
- 高压场景角色永远从容 → 真实生理反应（颤抖、喘息、失误）
- 连续段落长度高度一致 → 长短交错打破节奏
- AI过渡词堆砌（"值得一提的是/不禁/缓缓"）→ 场景化过渡

若判定"像AI"→ 标记为P1，要求重写关键段落。

### Step 5: 问题分级

| 级别 | 判定标准 |
|------|---------|
| P0 | 三视角冲突 / 因果链断裂 / 人物OOC / 术语违规 |
| P1 | 单视角严重问题 / 伏笔未回收 / 节奏断层 / Smell Test失败 |
| P2 | 单视角中等问题 / 描写冗余 / 对话平淡 |
| P3 | 轻微问题 / 标点不均 / 用词重复 |

### Step 6: 输出审阅报告

评级标准：A（前20%-25%）/ B（前25%-40%）/ C（中间40%-60%）/ D（后30%-40%）

报告输出到 `novels/{NOVEL_NAME}/审阅报告/正文审阅-{date}.md`

报告格式：
```markdown
# 审阅报告 - {章节范围} - {date}

## 总评：{等级}（{分数}/100）

## P0 问题（必须修复）
- [{类别}] {问题描述} | 位置：{文件}:{行号} | 建议修复：{具体方案}

## P1 问题（限1轮修复）
...

## P2 问题（可延期）
...

## 三视角审查
| 维度 | 读者 | 作者 | 人物 | 冲突 |
|------|------|------|------|------|
| Ch{N} | {评级} | {评级} | {评级} | {描述} |

## Smell Test
结论：{通过/不通过} | 不通过原因：{描述}

## 术语合规
违规数：{N} | 详情：{位置→替换建议}
```

> 此报告格式即为 **审阅报告数据协议**，novel-reviser 可直接解析。

---

## C4: 设定审查

```
Step 1: 全量加载设定数据
  world_query(novel_name=NOVEL_NAME) + character_list(novel_name=NOVEL_NAME)
  + relation_list(novel_name=NOVEL_NAME) + foreshadow_list(novel_name=NOVEL_NAME)
Step 2: 6维度深度审查
  ① 内部自洽：同维度内不同条目是否矛盾（如两条种族描述冲突）
  ② 人物一致：角色能力/出身/关系是否与世界观设定匹配
  ③ 物品合理：物品功能/稀有度/获取方式是否自洽
  ④ 历史可信：历史事件是否与当前状态逻辑一致（无未解决的遗留问题）
  ⑤ 关系完整：所有角色关系是否双向定义、无孤立节点
  ⑥ 伏笔可行：已埋伏笔的计划回收章是否合理、有无过期未回收
Step 3: 术语合规扫描
  加载 lorecraft/references/term-map.md → 全量扫描设定中的现代术语 → 标记违规
Step 4: 🔒 输出问题清单（P0/P1/P2分级）→ 每条附修复方案
Step 5: 执行修复 → world_upsert/character_update/foreshadow_update → 级联同步
Step 6: 验证修复 → 重跑 Step 2 确认无新矛盾
```

输出到 `novels/{NOVEL_NAME}/审阅报告/设定审查-{date}.md`

## C2: 健康诊断

```
health_check(novel_name=NOVEL_NAME) → 6指标：
- 伏笔积压率（阈值：>30% 需回收）
- 配角活跃gap（阈值：连续3章未出场需激活）
- 升级节奏（阈值：连续5章无能力变化需事件）
- 日常密度（阈值：连续3章纯日常需主线事件）
- 暗线推进（阈值：连续2卷无推进需植入线索）
- 卷完成度
```

低于阈值项 → 破局策略：加事件 / 减日常 / 回收伏笔 / 激活配角。

输出到 `novels/{NOVEL_NAME}/审阅报告/健康诊断-{date}.md`

## C3: 级联更新

```
Step 1: 确定变更范围
  用户指定变更内容 → character_update / world_upsert / foreshadow_update 执行
Step 2: 全量影响扫描
  db_search(novel_name=NOVEL_NAME, keyword={变更关键词}) → 扫描受影响的章节/人物/伏笔/时间线
  + character_list / relation_list / foreshadow_list 检查关联数据
Step 3: 🔒 展示修改影响清单
  受影响文件：{章节列表}
  受影响人物：{人物列表 + 关系变化}
  受影响伏笔：{伏笔列表 + 状态变化}
  受影响时间线：{事件列表 + 因果链变化}
  → 用户确认修改清单，输入"OK"继续或调整
Step 4: 执行级联修改
  按影响清单逐项修改（章节正文→人物档案→伏笔状态→时间线事件）
  修改 DB + sync_db_to_files()
Step 5: 一致性验证
  validate_chapter(受影响章节) + consistency_guard(novel_name=NOVEL_NAME, auto_sync=True)
  + 重跑受影响伏笔的回收检查
Step 6: 输出级联报告
  变更摘要 + 影响范围 + 修改条目 + 未修复项（如有）
```

> 局部修改在长篇中几乎不存在——改一个设定往往牵动多条人物线和时间线。db_search 让修改者看到完整"涟漪效应"。
> C3 优先级高于 B2（写作中断）。写作中说"改设定"→ 暂停写作，先处理级联更新。

</what-to-do>

<supporting-info>

## 审计工具加载

| 工具 | 用途 | 加载方式 |
|------|------|---------|
| outline-review | 大纲10维度审计 | skill_loader("novel-qa", "engine", "outline-review") |
| causality | 因果逻辑审计 | skill_loader("novel-qa", "engine", "causality") |
| anti-ai | AI指纹检测(F1-F16) | skill_loader("novel-qa", "engine", "anti-ai") |
| item | 物品一致性 | skill_loader("novel-qa", "engine", "item") |
| author-voice | 作者声音定义 | skill_loader("novel-qa", "engine", "author-voice") |
| term-map | 术语合规映射 | lorecraft/references/term-map.md（强制） |
| 三视角Agent | 读者/作者/人物审查 | engines/reader-perspective-agent.md 等 |

## 与 novel-reviser 的数据交接

审阅报告格式遵循 Step 6 定义的 Markdown 结构。novel-reviser 解析规则：
- P0/P1 问题从 `## P0 问题` / `## P1 问题` 章节提取
- 位置信息从 `位置：{文件}:{行号}` 字段提取
- 修复建议从 `建议修复：{具体方案}` 字段提取
- 术语替换从 `## 术语合规` 章节提取

## 边界条件

| 场景 | 处理 |
|------|------|
| 审阅文件不存在 | `Read` 失败 → 提示用户确认文件路径，或跳过该文件 |
| validate_chapter 返回 violations | 记录为 P1 问题，纳入问题清单，novel-reviser 修复 |
| 审阅报告解析失败 | 报告格式不匹配 → 尝试宽松解析（按 markdown 标题提取），仍失败则提示手动标注 |
| health_check DB 空数据 | 新项目无数据 → 提示"尚无写作数据，请先完成世界观+人物设计" |
| db_search 无结果 | 变更未影响其他数据 → 仅修改目标数据，跳过级联 |
| Smell Test 不通过 | 标记为 P1 → 🔒展示不通过原因 → 用户确认是否接受/要求重写 |

</supporting-info>
