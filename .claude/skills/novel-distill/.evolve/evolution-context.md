## R1 — 2026-06-04
- **策略**：S2 工作流重组 + 批露式架构
- **为什么改**：蒸馏内容通用模板无差异、无法部分下锅、子agent无策略、架构需批露式
- **改了什么**：
  1. Phase 0 新增类型识别（8类型信号表）+ 维度优先级映射（9类型映射表）+ 文件校验
  2. Phase 1 新增作品画像（work_profile + dimension_density）
  3. Phase 2 改为批露式架构：6个维度模块（agents/dim-*.md）+ skill_loader加载元skill方法论 + 子agent并行调度
  4. Phase 2c borrowable独立存储 + 向量索引验证 + ctx_index codemap
  5. Phase 3 下游消费指引 + 三层检索协议
- **痛点解决**：PP-1→resolved, PP-2→resolved, PP-3→resolved, PP-4→resolved, PP-5→resolved
- **结果**：评分 49→77（audit），T_train 12/12，5痛点全解决无回归
- **遗留**：无

## R2 — 2026-06-04
- **策略**：S2 工作流重组 + S3 边界增强（将夜真实蒸馏执行痛点驱动）
- **为什么改**：R1部署后发现子agent输出难提取、中文原文触发内容安全过滤、蒸馏结果只存DB不存文件人看不了、下游skill不知道怎么消费蒸馏数据
- **改了什么**：
  1. Phase 2b prompt模板加入输出格式契约（必须写入/tmp/distill-*.json）+ 文学分析语境声明（防API安全过滤）
  2. Phase 2b 加入维度模块精确名称映射表（characters复数其余单数）+ ls验证步骤
  3. Phase 2c 加入文件输出（参考/{作品名}/蒸馏报告.md + borrowable-{维度}.md）+ 批量写入策略（>20条分批并行haiku）+ 向量验证降级
  4. Phase 3 加入下游知识注入：更新CLAUDE.md参考作品区 + ctx_index注入检索摘要
  5. 质量保障从7条增至11条（新增：文件持久化/下游注入/文学语境/命名一致性/输出校验改路径）
- **痛点解决**：PP-6→addressed, PP-7→addressed, PP-8→addressed, PP-9→addressed, PP-10→addressed, PP-11→addressed, PP-12→addressed, PP-13→addressed
- **结果**：v3.0.0→v3.1.0，评分 77→79（audit），8痛点全部 addressed，0 FAIL 7 WARN
- **遗留**：PP-10（vector_search MCP bug）为外部依赖，降级处理但不根治

## R3 — 2026-06-04
- **策略**：S4 context-optimization（上下文优化）+ S2 workflow-reorg（borrowable 写入去子agent化）
- **为什么改**：将夜蒸馏实战 token 分析发现 3 大浪费源：(1) 45 条 borrowable 用 4 个 haiku agent 写入（17.6KB prompts 浪费）(2) db_search 无 top_k 拉回 49 条全量结果（~15KB）(3) 维度记录内嵌完整 borrowable 与 ref_borrowable 双重存储
- **改了什么**：
  1. Phase 2c borrowable 批量写入改为"主 agent 直接 FOR 循环"（去掉子 agent 条件分支）
  2. 所有 db_search 调用加 top_k 参数（5/10），质量规则#12 强制
  3. 新增维度记录去重规则：data 只存 borrowable_summary（count+patterns），完整数据唯一存 ref_borrowable
- **痛点解决**：PP-14→resolved, PP-15→resolved, PP-16→resolved
- **结果**：评分 79→84（audit），0 FAIL 3 WARN，0 FM-PP 回归
- **遗留**：WARN-2/3/4 为非阻塞性改进，下一轮顺手处理

## R4 — 2026-06-04
- **策略**：S0+S3+S4 合成（trace-driven + 边界增强 + 上下文优化）
- **为什么改**：用户反馈 borrowable 检索后仍需人工判断适配性——缺 source_context（原文设定基底）、elements（可替换组件）、adaptation_map（keep→replace 映射）。要求蒸馏数据跨项目通用，不做特定作品预适配。
- **改了什么**：
  1. Phase 2b: borrowable JSON schema 扩展 3 字段 + 6维度差异化 elements/adaptation_map 结构映射表（S3）
  2. Step 2c: 输出校验链（complete/partial_quality 质量标记 + 占位降级 + 用户报告）（S3）
  3. Phase 3: 蒸馏报告"适配判断"列 + L1.5 adaptation_map 检索 + adaptation_map 缺失降级指引（S4）
  4. 核心概念: 跨项目通用设计原则 + adaptation_map 使用原则（S0）
  5. 质量规则 14-16 + 禁止 2 条（禁止具名替换 + 禁止预适配）
- **痛点解决**：PP-17→resolved
- **结果**：v3.3.0→v3.4.0，84→91（+7），审计 0 FAIL 2 WARN 1 INFO，0 FM-PP 回归
- **遗留**：Step 3.2 空段落（继承债务）、top_k=50 与规则 ≤10 需例外说明
