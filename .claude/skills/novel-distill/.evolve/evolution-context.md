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
- **遗留**：PP-10（vector_search MCP bug）为外部依赖，降级处理但不根治；D5 输出契约和文学语境声明需下次蒸馏实战验证
