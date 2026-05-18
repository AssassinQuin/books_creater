---
name: novel-qa
description: 小说全链路质量保障。触发词：审阅/检查/诊断/改设定/OOC/卡文
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*
lifecycle: quality
---

# 小说质量保障

<what-to-do>

## 强制流程

```
B3审阅: 加载上下文 → 3Agent并行扫描 → 🔒评分卡 → 汇总报告 → 存盘
C4设定审查: 全量加载 → 6维度审查 → 🔒问题清单 → 修复 → 级联同步
C2诊断: health_check → 指标对比 → 🔒破局方案
C3更新: 改数据 → db_search找影响 → 🔒确认 → 执行 → 验证
```

输出到 `novels/{小说名}/审阅报告/`。无文件输出 = 流程未完成。

## 问题分级标准

| 级别 | 判定标准 | 处理要求 |
|------|---------|---------|
| P0-致命 | 因果链断裂/人物OOC/设定矛盾/违禁词/**禁止术语** | 必须修复，阻断发布 |
| P1-严重 | 伏笔未回收/节奏断层/质量方差超限/**新术语无文化出处** | 必须修复，限1轮内 |
| P2-中等 | 描写冗余/对话平淡/爽点不足 | 建议修复，可延期 |
| P3-轻微 | 标点不均/用词重复/格式不统一 | 可选修复，批量处理 |

</what-to-do>

<supporting-info>

## B3: 大纲审阅（触发：审阅大纲）

加载：`skill_loader("novel-qa", "engine", "outline-review")`

Phase 1: 10维度Agent审计（结构/起承转合/伏笔密度/人物弧光/支线检验/情绪曲线/悬念密度/世界观一致性/因果链/可读性）
- 因果链断裂 → 自动判P0，参考 `skill_loader("novel-qa", "engine", "causality")`
Phase 2: P0/P1修复（每问题3方案+代价评估）
Phase 3: 重评，综合≥85通过，最多3轮

## B3: 正文审阅（触发：审阅正文/校对）

Step 1: 加载上下文
  - 角色状态（`character_get` + `chapter_get_context`）
  - 卷级大纲（`novels/{小说名}/设定/大纲/V{卷号}-{卷名}.md`）
  - 全书支线总图（`novels/{小说名}/设定/大纲/支线总图.md`）
  - 世界观数据（`world_query(novel_name="这次不一样了")` 优先；返回空时回退读 `设定/世界观.md`）
  - 作者声音定义（`engines/author-voice.md`）
  - 🔒 术语规范（`lorecraft/SKILL.md` + `lorecraft/references/term-map.md` — 正文审阅必须检查禁止术语）

Step 2: 5Agent并行扫描
  - Agent-人物: OOC检测/知识矛盾/说话风格一致性/关系合理性
  - Agent-逻辑: 时间线连贯/经济系统一致/伏笔回收状态/物品使用逻辑
  - Agent-质量: 战斗场面质量/章节结构/爽点分布/NPC活跃度/写作风格/AI指纹(F1-F6)
  - **Agent-术语: 术语合规审查** — 加载 `lorecraft/references/term-map.md`，逐章扫描禁止术语（数据/系统/信号/参数/权限/终端/频率等），标记违规位置 + 按映射表给出替换建议；检查新术语是否有文化出处；检查势力/能力/地点术语是否与已注册元素一致
  - **Agent-支线: 支线完整性审查**
    - 本卷支线节点是否按全书总图执行
    - 支线-主线交织方式是否清晰
    - 支线角色出场是否突兀
    - 支线三检验是否通过
  - **Agent-三视角: 3个独立Agent并行审查**
    - Agent-读者: 加载 `engines/reader-perspective-agent.md` → 按**章节级标准**审查（开头钩子/信息不跳级/悬念管理/角色识别/场景定位/情感共鸣/结尾期待/逻辑跳跃/设定突兀/人物行为/时间线）
    - Agent-作者: 加载 `engines/author-perspective-agent.md` → 按**章节级标准**审查（起承转合/伏笔操作/节奏变化/主题传达/结构力度/信息投放/场景结构）
    - Agent-人物: 加载 `engines/character-perspective-agent.md` → 按**章节级标准**审查（POV行为符合性格/对话符合风格/知识边界/动机充分/情感反应真实/选择有代价/微表情动作）
    - 交叉检查: 读者vs作者/读者vs人物/作者vs人物（由编排器汇总后执行）

Step 3: `validate_chapter(chapter_text)` 硬约束复核（写时自检的补充，不替代）
Step 4: 问题分级 P0/P1/P2/P3
  - P0: 三视角冲突（人物逻辑 vs 作者结构）/因果链断裂/人物OOC
  - P1: 单视角严重问题/伏笔未回收/节奏断层
  - P2: 单视角中等问题/描写冗余/对话平淡
  - P3: 轻微问题/标点不均/用词重复
Step 5: 输出审阅报告 → 评级 A(≥90)/B(≥80)/C(≥70)/D(<70)
  - 报告必须包含三视角审查结果

AI指纹检测：`skill_loader("novel-qa", "engine", "anti-ai")`

## C4: 设定审查（触发：审设定）

1. `world_query` + `character_list` + `relation_list` + `foreshadow_list` 全量加载
2. 6维度审查：内部自洽/人物一致/物品合理/历史可信/关系完整/伏笔可行
3. 🔒问题清单 → 修复方案 → 执行 → 级联同步（受影响的章节/人物/伏笔）

## C2: 健康诊断（触发：诊断/卡文）

`health_check(novel_name="这次不一样了")` → 6指标：伏笔积压率/配角活跃gap/升级节奏/日常密度/暗线推进/卷完成度
→ 低于阈值项 → 破局策略（加事件/减日常/回收伏笔/激活配角）

## C3: 级联更新（触发：改设定/改人物）

1. 更新数据
2. `db_search(novel_name="这次不一样了", 关键词)` 扫描全部影响范围
3. 🔒确认修改清单（影响章节/人物/伏笔/时间线）
4. 执行修改
5. 验证一致性

## 审计工具加载

`skill_loader("novel-qa", "engine", "item")` 物品一致性
`skill_loader("novel-qa", "engine", "causality")` 因果逻辑审计
`skill_loader("novel-qa", "engine", "anti-ai")` AI指纹检测
**`Read(".claude/skills/lorecraft/SKILL.md")` + `Read(".claude/skills/lorecraft/references/term-map.md")` 术语合规审计（强制——正文审阅必须执行）**

</supporting-info>
