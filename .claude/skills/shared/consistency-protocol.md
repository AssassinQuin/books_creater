# 一致性校验协议

## 适用场景
任何 skill 在开始工作前，需要确保 DB 与文件数据一致时使用。

## 核心原则
- DB 是权威源，文件是人可读副本
- 不一致时自动同步（auto_sync=True）
- 跳过会导致后续 Agent 基于过时信息工作

## 执行步骤

1. 调用 `consistency_guard(novel_name="NOVEL_NAME", auto_sync=True)`
2. 守卫自动检测 DB hash 变更 → 同步到文件
3. 一个调用覆盖所有实体类型，无需逐个遍历

## 调用时机

| 时机 | skill |
|------|-------|
| Step 0 数据采集前 | novel-planner, novel-planner-volume, novel-chapter-writer |
| 写作完成后 | novel-chapter-writer Step 6 |
| 级联更新后 | C3-update |

## 失败处理

| 场景 | 处理 |
|------|------|
| DB 连接失败 | 阻断，提示检查 MCP 服务 |
| 同步部分失败 | 继续执行，记录未同步实体 |
| 文件写入权限不足 | 提示用户检查文件权限 |

## 为什么不可跳过

Agent 2 通过 MCP 创建新实体时写入 DB，`consistency_guard` 自动同步到文件。跳过会导致：
- 设定文件与 DB 不一致
- 后续 Agent 读取时基于过时信息
- 角色状态错误或伏笔冲突
