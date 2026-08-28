---
name: novel-chapter-writer
description: 逐章写作引擎（达尔文版骨架 + story 工作流纪律）— 场景路由、prose_pack 写前准备三步曲、细纲优先边界、字数验证、写后同轮清零、日更串行批量、修订事务。触发词：写第N章/继续写/写一章/日更/续写/回炉/重写第X章。
---

# 逐章写作引擎（novel-chapter-writer）

> 达尔文版骨架（场景类型策略/多线交织）+ 写作纪律层（写前准备三步曲/细纲优先边界/同轮清零/日更控制，源自 2026-08-27 写手写作逻辑调研）。

## 场景路由

| 场景 | 触发条件 | 执行 |
|------|----------|------|
| **大修/回炉** | "修改第X章"/"回炉"/"重写第X章" | 修订流程（见下） |
| **写指定章** | "写第N章"/"开书并写首章" | 单章序列；无细纲先补（plot-planner）再写点名章 |
| **日更续写** | "日更"/"续写"/"继续写" 且已有正文+追踪 | 日更批量（见下） |
| **开书** | "开书"（空项目） | 提示走 novel-setup→planner；默认停在细纲交付 |

**匹配优先级**：大修 → 写指定章 → 日更 → 开书。**裸调用**（无明确意图）→ `book_status` 诊断 + 列选项（"写第1章"/"日更2章"/"逐章确认"/"修改第X章"），不得自动进正文、不得把已有项目默认为日更 3 章。

---

## 单章序列（顺序不可跳）

1. **细纲检查**：`outline_next` 取本章细纲。缺失 → 补纲流程（spawn plot-planner 单章补建，无法确认的字段写 `[待补充]`），补齐才继续。
2. **prose_pack 注入**：`prose_pack(chapter=N)` 打包并记账（hook 凭账本放行写入）。**gaps 分支**：
   - `missing_primary_contract=true` → ⛔ 停止，按 `repair_action` 修复（走 story-flow 的「对标拆书」采集流程，补齐 `对标/{书}/剧情/情绪模块.md` 与 `节奏.md`），不得进正文
   - `no_benchmark=true` → 情绪/节奏目标从细纲「情绪」、卷纲、题材定位内部取，标注"无对标参考"
   - `custom_style=true` → `设定/文风.md` 作权威风格基，对标文风降为参考
3. **写前准备三步曲**：
   - **状态筛选**：pack 已含状态卡/角色快照/伏笔视图；只取本章相关（活跃伏笔、下一章承诺、涉及角色）
   - **模块召回**：从 pack 的情绪模块选 1 个 `selected_emotion_module`（与本章目标情绪最贴近）；从节奏选 1 条 `rhythm_reference`；有对标匹配章则读其技法。**答不出"本章目标情绪词/借鉴哪个技法/用在哪些段落"→ 回读 pack 再动笔**
   - **意图确认**：一句话写清本章意图（例：「快节奏打脸——账单暴露→逼问→反证→公开代价；读者等了三章，这章必须一拳到位」）
4. **标题预检**：细纲章名与既有章节重复 → 按核心事件改名，同步细纲与文件名。
5. **spawn chapter-writer 写正文**：任务提示 = pack 全文 + selected_emotion_module + rhythm_reference + 意图确认 + 字数目标 + **细纲优先边界**。产出 `novels/{书名}/正文/第NNN章_标题.md`。
6. **字数验证**（写完第一件事）：实际字数 vs 细纲 `字数目标`（缺目标按 3000 代入并提示补纲）。
   - < 90%：密点（爽点/打脸/反转）写薄 → 重写到目标区间；低压/关系章 → 补细纲内已有铺垫互动；细纲没有可展开内容 → **输出 `outline_underfilled` 欠账点清单，补纲/确认后再写，禁止自造新剧情凑字**
   - > ×1.1：压过场、合并疏点，不删主线爽点
7. **检查**（可证伪核对，不达标→修复）：**每章三件套**——信息增量（新线索/新设定）+ 冲突升级（更大麻烦）+ 情绪落点（爽/甜/燃），缺一即欠账；**每 500 字一个甜头**（小悬念/小反转/小震惊），连续 1500 字无情绪刺激=断档要补；① 爽点出手前是否有可指认的危机/期待段落（指不到具体情节点=空洞→补铺垫），爽点四步齐了吗（期待感→压迫→反转→回报）；② 装逼/打脸/揭露章：反派压制≥3次且逐次升级、围观者够多、在场配角差异化反应（不是集体震惊模板）；③ 任务卡点是否卡出信息/关系/代价/选择/伏笔变化（没有就不强补，删掉无损就压缩）；④ **章尾接新期待**——爽点兑现的章尾必须立即埋出/接上下一个期待（满足性弃书是追读第一杀手：爽完的瞬间就是动力消失的瞬间）。低压章不强求爽点，但章尾要有往下看的理由。
8. **元信息扫描**：标题行外不得出现 `第X章/上一章/前文/后文/伏笔/细纲/读者` 等工程词 → 改写为场景内锚点（"比第一章那三秒"→"比那三秒"）。例外：角色在故事内真实阅读/讨论文本。
9. **写后同轮清零**：正文落盘不是汇报时机——**同一轮内**跑完 `ai_check(N)` blocking 清零 + 禁词分级处理（一级命中即换；最毒句式五连查：①「不是A而是B」全家族 ②声线反差"声音不大…却…" ③"，带着…"万能状语 ④预告/总结收尾 ⑤短词引号强调），不得先汇报"已写完"再等指示。hook 推回的毒句式当轮清零。**唯一豁免**：用户显式说"本章不去味"→ 标题行下加 `<!-- 去味:跳过 -->`。
10. **tracking_commit**（立即，不可跳）：组装本章事务（schema 见文末「事务 JSON 实测 schema」附录），`expected_state_revision` 取 `tracking_check` 的当前值；成功取得新 revision 才算完章。失败按类型：写入失败→重跑同一事务；校验失败→改事务再提。**修订正文改变连续性事实时 → mode=revision 事务重交该章完整记录**。
11. **git commit** `ch{N}: {标题}`。

### 修订/回炉流程（大修场景）

1. `context_pack(X)` + 读原细纲 → 确认修改范围（措辞级 or 事实级）
2. 措辞级：直接改文 → `ai_check` 清零 → 纯措辞不重复提交事务
3. 事实级（改了事件/伏笔/角色状态/时间线）：改文 → `ai_check` 清零 → **mode=revision 事务**（伏笔用 foreshadow_changes 更新同 ID，不追加历史；作者秘密不得泄进读者视图）
4. 涉及后续章节 → 列受影响细纲，提示用户

---

## 日更批量纪律

- **串行不并发**：主会话内逐章串行；多章绝不并发写（上下文断裂/追踪覆盖/标题去重失效）
- **continuation 规则**：进入日更后"继续/续写/日更"= 继续当前批量流程，不得跳过写前准备直接续写，也不得每章问"是否继续"；到本轮上限（默认 2-3 章，单轮最多 3 章）必须收尾停止
- **暂停条件**（仅这些）：细纲缺失、章节号冲突、请求会改大纲/追踪、用户要求逐章确认
- **上一章欠账检查**：写本章前确认上一章无未清 blocking 毒句式（写前 hook 会拦）；有欠账先清（豁免标记除外）
- **久别角色**：细纲涉及角色不在状态卡 `核心角色状态` → 读 `追踪/角色状态/{名}.md` 小快照（pack 已自动注入）；缺失=检查点损坏 → `tracking_check` + 重跑事务修复，不手写替代
- **旧信息查找分级**（单章步骤合计>3 次=细纲没写清要消费哪些旧信息，批末提示补纲）：状态卡已有→直接用 → 伏笔ID grep 伏笔.md / 角色查快照 / 时间线查视图 → 定点 grep 逐章记录（tail 5）→ 单章增量/正文。**日更禁止全量读逐章记录/正文**
- **漂移三档**：aligned=按计划；adaptive=细节适配不改契约；structural=正文改了卷契约/单元承诺/兑现归属 → 必须修正文或重规划细纲，不能只备注。下章必须修的进 `next_chapter_commitments`，跨章风险进 `continuity_risks`
- **中途快照**（每连续 3 章）：`tracking_check` + `ls 正文/` 确认文件大小正常（>100 bytes）
- **批末收尾**：本批整体复扫 `ai_check`（确认无回潮）+ 标题去重 + `tracking_check`，汇报章数/字数/漂移/下批建议；**不再补写任何追踪内容**（每章已即时事务）

## 追踪纪律（borrowed from story tracking 体系）

- 完整 `_tracking-state.json` **不进 prompt**；章号/修订号从 `tracking_check` 紧凑输出取
- 状态只经 `tracking_commit` 事务；派生视图（上下文.md/伏笔.md/角色状态/时间线）不手改
- 退役显式声明：不再成立的约束/退场角色写 `retired_context_items` / `retired_characters`（漏写会被工具拒绝）
- 长期约束 ≤6 条；续写状态卡固定 7 栏 ≤12KB；逐章记录 ≤3072 字节——超限由工具校验拒绝，不自行裁剪绕过


---

## 事务 JSON 实测 schema（2026-08-28 端到端验证）

**commit 事务**（经 `mcp__story-flow__tracking_commit`）：

```json
{
  "schema_version": 1,
  "mode": "append",              // append（新章，chapter=last+1）| revision（回炉，chapter≤last）
  "chapter": 1,
  "chapter_title": "标题",
  "expected_state_revision": 0,  // 取 tracking_check 返回的当前值（乐观锁）
  "delta": {
    "result": "本章结果一句话（只写影响后续的部分）",
    "character_changes": [{"name": "陈默", "change": "变化描述"}],
    "foreshadow_changes": [{"id": "F001", "summary": "…", "planted_chapter": 1,
      "planned_resolution_chapter": 5, "status": "已埋", "importance": "高"}],
    "timeline_events": [{"id": "E001", "story_time": "…", "objective_fact": "作者真相",
      "reader_knowledge": "读者已知", "reveal_status": "已揭示", "reveal_chapter": 1, "characters": ["…"]}],
    "constraints": [],
    "next_chapter_commitments": ["下章必须履行的承诺"],
    "retired_context_items": [],
    "retired_characters": []
  },
  "context": {
    "position": {"volume": "第一卷", "volume_start_chapter": 1, "story_time": "…", "scene": "…"},
    "long_term_constraints": ["≤6条，不再成立的写 retired_context_items"],
    "active_character_names": ["≤6人"],
    "continuity_risks": ["≤5条"]
  },
  "character_snapshots": {
    "陈默": {"identity": "…", "location": "…", "goal": "…", "state": "…",
      "abilities_resources": ["…"], "relationships": [], "knowledge": ["…"], "open_threads": ["…"]}
  }
}
```

**硬枚举**：伏笔 status `已埋/已回收/已过期/放弃`；importance `高/中/低`；reveal_status 见 `追踪/时间线/` 视图口径。ID 格式固定：伏笔 `F001`、事件 `E001`。

**init 文档**（`tracking_init`，新书第 0 章）：顶层 `schema_version:1, book_title, last_chapter, context(含 recent_chapters/next_chapter_commitments 初始可空), character_snapshots, foreshadow, timeline_events`。

**纪律**：摘要写 `delta.result`（≤360字节，只记影响后续的）；`recent_chapters`/活跃伏笔由工具派生，不手填；`context` 每次完整重交（退役条目必须显式声明，漏写被拒）；核心角色变化必须同时交 `character_changes` + 顶层完整快照。
