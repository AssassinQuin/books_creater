# 故障乌托邦-unknown-均匀短章翻页引擎


> **条目名**：故障乌托邦-unknown-均匀短章翻页引擎

## 概览

- **region**: 全域

## 详细设定

### source_work

故障乌托邦

### source_dimension

unknown

### pattern_name

均匀短章翻页引擎

### pattern_detail

641章、平均51行/章的极度均匀短章体制，降低阅读门槛并鼓励'再翻一章'

### source_context

在面向移动端阅读的长篇小说中，通过控制章节长度的均匀性和极短标题来降低阅读决策成本

### elements

    - **technique**: 长度均匀化
    - **trigger_chapter**: 全书
    - **effect**: 读者建立稳定的阅读节奏预期
    - **frequency**: 全局约束
    - **technique**: 超短标题
    - **trigger_chapter**: 全书（92%标题≤3字）
    - **effect**: 标题不剧透、不描述、只给一个关键词，降低信息噪音
    - **frequency**: 92%的章节

### adaptation_map

    - **aspect**: 章节长度
    - **original**: 平均51行/章
    - **abstract_role**: 阅读决策成本
    - **replacement_guide**: 根据目标平台调整：移动端2000-3000字/章，PC端可更长但保持均匀
    - **aspect**: 标题策略
    - **original**: 92%≤3字关键词
    - **abstract_role**: 标题信息控制
    - **replacement_guide**: 标题只给一个意象或关键词，不概括剧情：用'雪'不用'雪夜中的逃亡'

### applicability

inspire

### applicable_genres

- 网文
- 移动端阅读
- 章节体

### 示例

641章，平均51行/章。章节标题也极短（平均2.2字），592章标题<=3字。短标题+短内容=低阅读门槛高翻页率。

### source_chapters

全书（统计分布）

### quality

complete

