# 第一序列-ability-基因序列分级（T1-T5）


> **条目名**：第一序列-ability-基因序列分级（T1-T5）

## 概览

- **region**: 全域

## 详细设定

### source_work

第一序列

### source_dimension

ability

### pattern_name

基因序列分级（T1-T5）

### pattern_detail

通过基因药剂改造人体，按T1-T5分级，每级对应固定倍数的身体素质提升，但受限于个体基因上限，且高等级会缩短寿命。

### source_context

火种公司为延续人类火种而进行基因改造，T1为1.5倍成年人体质，T2为2倍，T3为3倍，T4为5倍，T5为7倍。但基因改造会缩短寿命，T5大多死于癌症。火种因此寻找001号实验体（完美基因）来补全缺陷。

### elements

    - **component**: 等级数值
    - **value_range**: T1=1.5倍/T2=2倍/T3=3倍/T4=5倍/T5=7倍成年人体质
    - **constraint**: 受个体基因上限限制，大部分人只能到T1-T2
    - **progression**: 指数（后期每级提升幅度增大）
    - **component**: 寿命代价
    - **value_range**: T5平均寿命<40岁
    - **constraint**: 基因改造导致免疫系统混淆，易患癌症
    - **progression**: 指数（等级越高代价越大）
    - **component**: 基因上限
    - **value_range**: 出生时基因决定T序列上限
    - **constraint**: 无法通过后天的努力突破基因天花板
    - **progression**: 固定

### adaptation_map

    - **aspect**: 等级数值设计
    - **original**: T1-T5固定倍数提升
    - **abstract_role**: 提供清晰可量化的战力标准
    - **replacement_guide**: 替换为任何数值化分级体系，需确保每级差距明显且可感知（如速度/力量/恢复力的具体倍数）
    - **aspect**: 寿命代价
    - **original**: T5因基因改造患癌症短命
    - **abstract_role**: 阻止战力膨胀的真实代价，强调'力量不是免费的'
    - **replacement_guide**: 替换为任何与力量强度正相关的不可逆代价，如精神崩溃、身体畸变、情感丧失等
    - **aspect**: 基因天花板
    - **original**: 个体基因上限决定T序列等级
    - **abstract_role**: 制造阶层固化与悲剧性，强调命运的不公
    - **replacement_guide**: 替换为血统/天赋/出身等先天决定因素，需与后天努力形成张力

### applicability

adapt

### applicable_genres

- 科幻
- 废土末世
- 军事
- 赛博朋克

### 示例

火种公司T5战士可正面抗衡超凡者，但T5因基因改造导致免疫系统混淆，极容易患癌症，至今没人见过活到40岁的T5。

### source_chapters

卷3-卷5（T序列登场、T5斩首部队、P5092解释基因缺陷）

### quality

complete

