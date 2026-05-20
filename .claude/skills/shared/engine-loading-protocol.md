# 引擎加载协议

## 适用场景
任何 skill 在启动 Agent 之前，需要加载引擎文件并验证加载完整性时使用。

## 输入

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| engine_list | dict | ✅ | {step_name: [engine_name]} 每步需要的引擎清单 |
| skill_name | str | ✅ | 当前 skill 名称，用于 skill_loader |
| lorecraft_required | bool | ❌ | 是否需要术语规范（默认 True） |

## 执行步骤

1. 按 step 顺序调用 `skill_loader(skill_name, "engine", engine_name)` 加载引擎
2. 如需 lorecraft，加载 `lorecraft/references/core-principles.md` + `term-map.md` + `quickref.md`
3. 加载 `engines/world-element-registry.md`（如 lorecraft_required）
4. 验证全部加载成功
5. 失败时阻断并提示用户

## 验证逻辑

```python
loaded = {}
for step, engines in engine_list.items():
    for eng in engines:
        content = skill_loader(skill_name, "engine", eng)
        loaded[f"{step}-{eng}"] = bool(content and len(content) > 10)

if lorecraft_required:
    for f in ["core-principles", "term-map", "quickref"]:
        content = Read(f".claude/skills/lorecraft/references/{f}.md")
        loaded[f"lorecraft-{f}"] = bool(content and len(content) > 10)
    content = Read(".claude/skills/engines/world-element-registry.md")
    loaded["world-element-registry"] = bool(content and len(content) > 10)

failed = [k for k, v in loaded.items() if not v]
if failed:
    print(f"⚠️ 以下资源加载不完整：{failed}")
    print("请缩短其他内容或分批处理。")
    return False
else:
    print(f"✅ 全部 {len(loaded)} 个资源加载成功")
    return True
```

## 失败处理

| 场景 | 处理 |
|------|------|
| 引擎文件不存在 | 阻断，提示用户检查 engines/ 目录 |
| 引擎文件为空 | 阻断，提示文件可能损坏 |
| 上下文不足 | 提示用户分批处理或启用分层加载 |
| lorecraft 缺失 | 阻断（术语规范是强制依赖） |

## 加载策略

| Tier | 引擎 | 加载时机 |
|------|------|---------|
| Tier 0（铁律） | writing-constraints, anti-ai, anti-ai-patterns, causality | 始终加载 |
| Tier 1（基础） | writing-style, author-voice, world-element-registry | skill 触发时 |
| Tier 2（按需） | 其余 32 个引擎 | 执行对应 Step 时 |
