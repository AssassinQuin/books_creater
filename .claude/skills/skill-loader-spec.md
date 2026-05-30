# skill_loader MCP 工具规范

> 渐进式加载协议：按需加载 skill 子文件，用完即弃，下次重新加载最新版。

## 接口定义

```python
def skill_loader(
    skill: str,           # skill 名称，如 "novel-planner"
    level: str,           # 加载层级: "phase" | "engine" | "example" | "agent"
    resource: str,        # 资源名，如 "b1-volume" | "environment" | "dialogue"
    project: str = None,  # 项目专属覆盖，如 "{小说名}"
) -> str:
    """
    按 skill + level + resource 加载对应的 .md 文件内容。
    
    加载优先级（从高到低）：
    1. 项目专属覆盖: skills/{skill}/overrides/{project}/{level}/{resource}.md
    2. skill 专属:    skills/{skill}/{level}s/{resource}.md
    3. 全局共享:      skills/{level}s/{resource}.md
    
    返回: 文件内容（markdown 字符串）
    未找到: 返回空字符串 + 错误信息
    """
```

## 加载路径解析

### 示例 1: 加载卷规划阶段指令

```python
skill_loader("novel-planner", "phase", "b1-volume")
```

解析路径：
1. `skills/novel-planner/overrides/{小说名}/phases/b1-volume.md` — 存在则返回
2. `skills/novel-planner/phases/b1-volume.md` — 存在则返回
3. `skills/phases/b1-volume.md` — 存在则返回
4. 未找到 → 返回错误

### 示例 2: 加载环境引擎

```python
skill_loader("novel-chapter-writer", "engine", "environment")
```

解析路径：
1. `skills/novel-chapter-writer/overrides/{小说名}/engines/environment.md`
2. `skills/novel-chapter-writer/engines/environment.md`
3. `skills/engines/environment.md` ← 命中（全局共享）

### 示例 3: 加载对话示例

```python
skill_loader("novel-chapter-writer", "example", "dialogue")
```

解析路径：
1. `skills/novel-chapter-writer/overrides/{小说名}/examples/dialogue.md`
2. `skills/novel-chapter-writer/examples/dialogue.md`
3. `skills/examples/dialogue.md` ← 命中（全局共享）

## 项目专属覆盖机制

允许为特定项目覆盖全局引擎/阶段指令：

```
skills/engines/environment.md              # 全局默认
skills/novel-planner/overrides/{小说名}/engines/environment.md  # 项目专属覆盖
```

使用场景：
- 《{小说名}》的灵能环境与普通玄幻不同
- 某项目需要特殊的对话风格
- 某项目有独特的战斗规则

## 与现有 engine_detail 的迁移

| 现有调用 | 新调用 |
|---------|--------|
| `engine_detail('environment')` | `skill_loader("novel-chapter-writer", "engine", "environment")` |
| `engine_detail('dialogue')` | `skill_loader("novel-chapter-writer", "engine", "dialogue")` |
| `engine_detail('action')` | `skill_loader("novel-chapter-writer", "engine", "action")` |
| `engine_detail('item')` | `skill_loader("novel-chapter-writer", "engine", "item")` |
| `engine_detail('causality')` | `skill_loader("novel-planner", "engine", "causality")` |
| `rule_detail('{key}')` | `skill_loader("novel-chapter-writer", "engine", "anti-ai")` |

## 缓存策略

```python
# 单次会话内缓存（避免重复读取同一文件）
_cache = {}

def skill_loader(skill, level, resource, project=None):
    cache_key = f"{skill}:{level}:{resource}:{project}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    content = _load_from_disk(skill, level, resource, project)
    _cache[cache_key] = content
    return content

# 注意：缓存只在单次会话内有效
# 修改文件后，新会话自动加载最新版
```

## 错误处理

| 场景 | 返回 |
|------|------|
| 文件不存在 | `{"error": "NOT_FOUND", "paths_checked": [...]}` |
| 文件为空 | `{"error": "EMPTY_FILE", "path": "..."}` |
| 权限不足 | `{"error": "PERMISSION_DENIED", "path": "..."}` |

## 实施步骤

1. **novel-db MCP 服务端添加 `skill_loader` 工具**
   - 修改 `/Users/ganjie/skills/novel-db-mcp/server.py`
   - 添加 `skill_loader` 函数
   - 注册到 MCP 工具列表

2. **更新所有 SKILL.md**
   - 将 `engine_detail('xxx')` 替换为 `skill_loader(..., "engine", "xxx")`
   - 将 `references/xxx.md` 引用替换为 `skill_loader(..., "engine", "xxx")`

3. **迁移 references/ 文件**
   - 已完成的：engines/ + phases/ + examples/ 目录
   - 保留原有 references/ 作为兼容（逐步废弃）

4. **测试验证**
   - 每个 skill 触发一次，验证加载路径正确
   - 检查项目专属覆盖是否生效