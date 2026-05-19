# 章节模板

> 权威源：文件 `正文/第{NNN}章-{标题}.md`。DB `chapters` 表存元数据。

## DB 字段映射

| MD字段 | DB列 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| number | number | INT | ✅ | 章节序号 |
| title | title | TEXT | ✅ | 章节标题 |
| chapter_type | chapter_type | TEXT | ✅ | normal/transition/climax/filler/daily |
| outline | outline | TEXT | ✅ | 章节大纲 |
| volume_id | volume_id | INT | ✅ | 所属卷ID |
| status | status | TEXT | ✅ | planned/drafting/written/reviewed/published |
| pov_character_id | pov_character_id | INT | 可选 | 视角角色ID |
| time_in_story | time_in_story | TEXT | 可选 | 故事内时间 |
| location | location | TEXT | 可选 | 主要场景地点 |
| mood | mood | TEXT | 可选 | 章节情绪基调 |

## 文件格式

### 章节正文（`正文/第{NNN}章-{标题}.md`）

纯正文，不含注释/统计/审计备注。

### 创意蓝图（`创意决策/Ch{N}-创意蓝图.md`）

```markdown
# Ch{N} 创意蓝图

## 因果链确认
{逐事件验证}

## 场面设计
### 场面1 | 密度: {级别}
- 时间/地点: {文学化描述}
- 核心事件: {一句话}
- 人物及目标（角色矩阵）
- 微事件分配
- 伏笔操作
- 镜头序列
- 预计字数

## 叙事节奏
{情绪曲线+节奏断层+刀锋技法}

## 角色行为弧线
{每个出场角色的行为设计}

## 回响（Echo）
- 回响1: {source_event} ← Ch{source_ch} → {echo_description}
- 回响2: {source_event} ← Ch{source_ch} → {echo_description}

## 已创建的实体
- 新人物: {name} (ID={id})
- 新地点: {name}
- 新物品: {name}
- 新伏笔: {id}
- 新回响: echo_{id}（source_ch→echo_ch, type）
```

---

## 扩展机制

新增维度时：
1. 在 DB `chapters` 表新增列
2. 在 `chapter_plan` / `chapter_update` MCP 工具中新增对应参数
3. 在 `get_chapter_context`（tools_chapter.py）的返回值 dict 中追加新字段；同时更新 `_resolvers.py` / `tools_chapter.py` / `tools_writing.py` 中的对应查询
