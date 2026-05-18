#!/usr/bin/env python3
"""
全面命名规范审计 + 纪元修正 + 动植物/建筑/物品设计更新脚本

核心原则：
1. 不可什么都加"灵"——这是中世纪，不是科幻
2. 不可什么都加"纹路"——同质化扼杀世界观
3. 按命名方法论重命名：底层文化根脉→中层专业术语→表层口语
4. 不同势力/区域用不同命名风格——术语即身份
5. 纹路是技术术语，不进入日常物品名——就像我们不说"电路灯泡"而说"灯泡"
"""

import sqlite3
import json
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'novel.db')
NOVEL_ID = 1

# ═══════════════════════════════════════════════════════════════
# PART 1: 命名重命名方案
# ═══════════════════════════════════════════════════════════════

# 格式: (category, old_name, new_name, rationale)
# rationale: 重命名理由
RENAME_PLAN = [
    # ── 能力/物品类: "灵能XX" → 去掉"灵能"前缀 ──
    # 中世纪人不会说"灵能短刀"，他们就叫"短刀"或"震刃"
    ("ability", "灵能短刀", "震刃", "文化根脉:'震'出自虞渊震域体系,比'灵能短刀'有力量感;民间叫'短刀'"),
    ("ability", "灵能碎渣", "碎渣", "碎渣本身就是日常物,不需要'灵能'前缀;外围人就叫碎渣"),
    ("ability", "灵能碎片", "残晶", "文化根脉:'残'有残破感,'晶'点明本质;比'灵能碎片'有质感"),
    ("ability", "灵能罗盘", "探脉盘", "文化根脉:'探脉'出自堪舆术/风水学;比'罗盘'更贴合功能"),
    ("ability", "灵能陷阱", "惊雷阵", "文化根脉:'惊雷'有画面感;实际是碎渣弹触发,炸响如雷"),
    ("ability", "灵能引渡椅", "引渡椅", "'引渡'本身已含灵能含义,无需'灵能'前缀;民间叫'那把椅子'"),

    # ── 生物类: "灵能XX"→去掉前缀,用特征命名 ──
    ("bestiary", "灵焰龙蜥", "赤鳞", "文化根脉:'赤鳞'更有古意;猎人俗语叫'大火蜥'"),
    ("bestiary", "灵能蜂群", "玉蜂", "文化根脉:'玉'有灵能光泽感;蜂体半透明如玉"),
    ("bestiary", "灵能驮兽", "驮兽", "最日常的动物不需要修饰词;就像不说'动力牛'而说'牛'"),

    # ── 建筑类: 去掉"灵能""纹路"前缀 ──
    ("building", "灵疗院", "疗院", "'疗'已含灵能治疗含义;民间叫'石医院'"),
    ("building", "灵能学院", "纹学院", "'纹学'是学科名,学院教纹学;比'灵能学院'有中世纪质感"),

    # ── 植物类: "灵能XX"→用特征/文化根脉命名 ──
    ("plant", "灵晶花", "晶花", "花本身像水晶,'晶'已点明;比'灵晶花'更雅"),
    ("plant", "灵能苔", "夜苔", "文化根脉:发光苔藓,夜间可见;外围人叫'夜路苔'"),
    ("plant", "灵能菌丝", "灰丝", "灰绿色丝状菌丝,直观命名;纹路师叫'墨菌'"),
    ("plant", "灵能麦", "铁麦", "比普通麦硬,口感有金属味;'铁'取其硬,不是真铁"),

    # ── 日常物品类 ──
    ("daily_life", "灵能烤炉", "碎渣炉", "以燃料命名,更接地气;就像'柴火灶'不说'热能灶'"),

    # ── 经济类 ──
    ("economy", "灵站兑换券体系", "站券", "缩略命名,日常口语;'站券'比'兑换券体系'精炼"),

    # ── 核心设定: "灵能XX"体系名 → 精炼 ──
    ("core_setting", "灵能区域化觉醒", "地气觉醒", "文化根脉:'地气'出自风水学,灵能浓度=地气浓薄;比'灵能区域化'有古意"),
    ("core_setting", "灵能物品分级", "器物品阶", "文化根脉:'器物'出自《考工记》;'品阶'有中世纪等级感"),
    ("core_setting", "灵兽体系", "驯兽志", "文化根脉:'志'出自方志体例,比'体系'有文献感"),

    # ── 以下保留不变但增加口语层注释 ──
    # 灵枢 — 已是文化根脉命名(枢=枢纽,庄子天枢),保留
    # 灵晶 — 已固化为货币名,保留;民间叫"晶"或"石头"
    # 灵站 — 已固化,保留;民间叫"站"
    # 灵契 — 已有文化根脉(契=契约),保留
    # 灵衰症 — 已固化,保留;民间叫"灰病"
]

# ═══════════════════════════════════════════════════════════════
# PART 2: 物品类重命名 (item category的"纹路XX"泛滥)
# ═══════════════════════════════════════════════════════════════

ITEM_RENAME = [
    # 纹路是技术,不是前缀——我们不说"电路灯泡"而说"灯泡"
    ("item", "纹路代步车", "自走车", "功能命名:车自己走;比'纹路代步车'自然"),
    ("item", "纹路保暖衣", "暖衣", "衣服暖就行,不需要说技术原理;就像不说'电热毯'而叫'暖毯'"),
    ("item", "纹路保温壶", "暖壶", "同上;中世纪人就叫暖壶"),
    ("item", "纹路农具", "利器", "'利'=锋利省力;农夫叫'好锄头'不说'纹路锄头'"),
    ("item", "纹路净水囊", "净囊", "'净'=净化;去掉'纹路'和'水'冗余"),
    ("item", "纹路治疗台", "疗台", "'疗'已含义;去掉'纹路'冗余"),
    ("item", "纹路灯柱", "照柱", "'照'=照明;中世纪人不说'纹路灯'而说'照柱'"),
    ("item", "纹路灶台", "灵灶", "'灵'=灵能驱动;灶台是日常物,一个字就够区分普通灶"),
    ("item", "纹路记忆石", "录石", "'录'=记录;文化根脉:'录'出自《录异记》"),
    ("item", "纹路通讯板", "传讯石", "已部分在术语规范中定义;统一为传讯石"),
    ("item", "纹路锁", "认锁", "'认'=认主;比'纹路锁'直观"),
    ("item", "纹路锻造锤", "铸锤", "'铸'=铸造;纹路师叫'铸锤'不说'纹路锻造锤'"),
    ("item", "纹路阵盘", "阵盘", "'阵盘'已完整表达,不需要'纹路'前缀"),
    ("item", "纹路飞舟", "浮舟", "'浮'=悬浮;文化根脉:浮槎传说;比'飞舟'更雅"),
]

# ═══════════════════════════════════════════════════════════════
# PART 3: 新增内容 — 动植物、灵能变异植物
# ═══════════════════════════════════════════════════════════════

NEW_PLANTS = [
    {
        "name": "蚀骨藤",
        "keys": ["蚀骨藤", "腐蚀", "矿脉"],
        "secondary_keys": ["酸液", "矿道"],
        "tags": ["plant", "藤蔓", "变异", "矿业"],
        "content": """蚀骨藤不是天然植物——是灵能残渣在矿道深处与某种苔藓共生后的变异产物。藤蔓灰白色，像枯骨，碰到灵矿石就疯长。蚀骨藤分泌一种微酸性液体，能把灵矿石表面蚀出凹痕。矿工怕它——蚀骨藤蔓延的矿道灵矿石品质下降，因为表层被蚀掉了。但纹路师喜欢它——蚀骨藤蚀出的凹痕天然形成某种不规则纹路，偶尔会意外地具有功能。纹路师管这叫"天赐纹"，但百条蚀骨藤纹里可能只有一条有用。蚀骨藤的酸液稀释后可以做纹路墨的调和剂——让墨线更容易渗入灵矿石微孔。"""
    },
    {
        "name": "石心草",
        "keys": ["石心草", "化石", "荒原"],
        "secondary_keys": ["石核", "药草"],
        "tags": ["plant", "草本", "变异", "荒原"],
        "content": """石心草长在西部荒原的石缝里——根扎不进土，扎进了石头。整株草灰绿色，叶片硬得像铁片。最值钱的是根——根结成一个硬核，纹路师叫石心。石心不是真的石头，是灵能长期浸润后根组织矿物化的结果。石心磨粉入药，能缓解灵衰症的关节疼痛——不是治，是压住疼。外围赤脚大夫用石心草根煮水，让灵衰症患者泡手泡脚，疼痛能减轻半天。石心草在荒原上不难找，但石心大的难找——大部分石心只有米粒大，指甲盖大的已经算好货。"""
    },
    {
        "name": "血棘",
        "keys": ["血棘", "刺", "红汁"],
        "secondary_keys": ["麻醉", "猎刀"],
        "tags": ["plant", "灌木", "变异", "密林"],
        "content": """血棘是南方密林的特产——低矮灌木，枝条上长满暗红色尖刺。刺破皮肤后刺尖渗出暗红色汁液，像血。血棘汁液有麻醉效果——猎人把血棘汁涂在箭头上，射中的猎物会迅速失去知觉。教会裁判官的刑具上也涂血棘汁——不是为了杀人，是为了让受刑者无法昏过去。血棘木是做弓的好材料——弹性好、硬度够、灵能亲和度适中。南方猎人几乎人手一把血棘弓。血棘在密林外很难存活——需要高灵能浓度和湿热环境。"""
    },
    {
        "name": "霜骨木",
        "keys": ["霜骨木", "冻土", "白木"],
        "secondary_keys": ["寒气", "北境"],
        "tags": ["plant", "乔木", "变异", "北方"],
        "content": """霜骨木只长在北方冻土带——树干灰白如骨，树皮上有冰晶状的灵能沉积。砍开霜骨木，断面是白色的，纹路师说像"骨瓷"。霜骨木的木料极硬——比铁木还硬，但比铁木脆，用力过猛会裂。霜骨木最特殊的性质是寒气——即使砍下来做成家具，霜骨木仍在缓慢释放灵能寒气。壁盾军团用霜骨木做盾牌——举着霜骨木盾等于自带一片凉意，北境夏天行军时简直是恩赐，冬天就冻手。霜骨木的生长极其缓慢——一棵手腕粗的霜骨木要长一百年。北境冻土上的霜骨木林是壁盾军团的战略资源，外人砍一棵都要被追杀。"""
    },
    {
        "name": "蚀心蕈",
        "keys": ["蚀心蕈", "菌", "寄生"],
        "secondary_keys": ["孢子", "灵衰", "禁地边缘"],
        "tags": ["plant", "菌类", "变异", "危险"],
        "content": """蚀心蕈是最危险的灵能变异菌类——只在禁地边缘的极端高灵能区生长。菌盖漆黑如墨，菌褶深红，孢子是灰色的粉尘。蚀心蕈的孢子被吸入后会在肺部着床，以宿主体内灵能为养分生长。初期症状和灵衰症几乎一样——皮肤发灰、关节疼痛、体力衰退。区别在于灵衰症是灵能沉积堵塞循环，蚀心蕈是灵能被菌丝吸走。如果不处理，蚀心蕈会在三到六个月内长满整个胸腔，宿主咳出灰色孢子粉后死亡。研究院的保守派在秘密研究蚀心蕈——如果能控制它的生长，蚀心蕈吸灵能的能力可以用来"清洗"灵衰症患者的灵能沉积。这是以毒攻毒的思路，目前还只是理论。"""
    },
    {
        "name": "雾蕊花",
        "keys": ["雾蕊花", "雾", "海岸"],
        "secondary_keys": ["灵雾", "致幻"],
        "tags": ["plant", "花卉", "变异", "海岸"],
        "content": """雾蕊花长在东部海岸的礁石上——花瓣半透明，像一团凝固的雾。雾蕊花在清晨释放灵能雾气，方圆几步内雾气缭绕。雾蕊花的灵雾有致幻效果——闻久了会产生轻微幻觉，看到不存在的光和色彩。东部海岸的渔民说"雾蕊花开的时候别出海"——不是因为花有毒，是因为致幻状态下分不清方向。但雾蕊花的灵雾提纯后是一种珍贵的药材——低剂量能缓解灵衰症的神经疼痛，效果比石心草根强十倍。提纯技术只有研究院掌握，原料则靠海岸渔民采集。一朵雾蕊花只值几铜板，但提纯后的雾蕊精华一瓶值几十银币。"""
    },
]

NEW_BEASTS = [
    {
        "name": "铁背蛛",
        "keys": ["铁背蛛", "矿脉", "虫豸"],
        "secondary_keys": ["蛛网", "矿石"],
        "tags": ["bestiary", "虫豸", "矿区", "异灵"],
        "content": """铁背蛛不是矿晶蛛——它们更小、更常见、也更烦人。拳头大小，背甲灰黑如铁，在矿脉裂缝里结网。铁背蛛的网不像矿晶蛛那样有灵光——铁背蛛的网是物理性的，灰黑色的丝线缠在矿壁上，不仔细看以为是裂纹。矿工撞上铁背蛛网不是危险——是恶心。蛛丝黏在脸上手上，扯不断洗不掉，得用碎渣烧。铁背蛛本身没什么威胁——咬人一口跟蜜蜂蛰差不多。但铁背蛛网覆盖的矿壁无法被灵觉探测——蛛丝的灵能屏蔽效果比迷雾鳗还强，只是范围只有蛛网覆盖的那一小块。有些角级异灵会在巢穴入口挂满铁背蛛网——天然隐匿。"""
    },
    {
        "name": "骨鸦",
        "keys": ["骨鸦", "食腐", "尸鸟"],
        "secondary_keys": ["战场", "异灵"],
        "tags": ["bestiary", "牙", "食腐", "异灵"],
        "content": """骨鸦不是乌鸦——是灵能环境下变异的食腐鸟。翼展近两米，全身羽毛灰白色，像被灰烬浇过。骨鸦不是猎手——是食腐者。战场是它们的食堂。兽潮过后骨鸦群才来，啄食死去的异灵和人。骨鸦的消化系统特殊——它们能消化异灵的灵能结晶，排出低纯灵晶渣。猎人管骨鸦叫"扫灰的"——有骨鸦的地方就有尸体，有尸体的地方就有战事。壁盾军团把骨鸦的出现当作兽潮结束的标志——骨鸦来了，说明打完了。骨鸦对活人没兴趣，但如果你身上有灵衰症晚期的气息——那是将死之人的气息——骨鸦会跟着你，等。"""
    },
    {
        "name": "地伏花蛇",
        "keys": ["地伏花蛇", "花蛇", "密林"],
        "secondary_keys": ["拟态", "毒牙"],
        "tags": ["bestiary", "牙", "拟态", "异灵", "密林"],
        "content": """地伏花蛇是南方密林里最阴险的牙级异灵。它不像土隐蜥拟态石头——地伏花蛇拟态花。蛇身覆着鳞片，鳞片颜色鲜艳如花瓣，盘起来的时候像一朵落在地上的花。人走过去想摘——花张嘴咬你。地伏花蛇的毒不致命——被咬后肢体麻木六到八个时辰，动不了但意识清醒。然后它慢慢吞。教会的巡礼祭司在密林里被地伏花蛇咬过——整个巡礼队瘫痪在密林里等了半天，直到毒效消退才爬出来。此后教会要求密林行军必须带灵犬。"""
    },
    {
        "name": "铁喙鸦鹫",
        "keys": ["铁喙鸦鹫", "鸦鹫", "北境"],
        "secondary_keys": ["空中", "冻土"],
        "tags": ["bestiary", "角", "空中", "异灵", "北方"],
        "content": """铁喙鸦鹫是北方冻土上的空中霸主。翼展四五米，全身黑羽，喙部覆着灵能硬化的角质的壳——硬度堪比灵矿石。铁喙鸦鹫不是主动猎人的异灵——它们是机会主义者，抢猎人的猎物。猎人杀了一只角级异灵正要取晶，铁喙鸦鹫从天上俯冲下来一嘴啄走灵晶，然后飞走。铁喙鸦鹫的灵晶在胃里——它们吞灵晶，像鸡吞石子助消化。一只铁喙鸦鹫胃里可能有好几颗灵晶。猎人偶尔会专门猎杀铁喙鸦鹫取晶——风险比猎角级低，回报差不多。但铁喙鸦鹫视力极好，人还没靠近就飞走了。只有壁盾军团的弩手能射下来。"""
    },
    {
        "name": "灰棘鱼",
        "keys": ["灰棘鱼", "棘鱼", "河鱼"],
        "secondary_keys": ["毒刺", "淡水"],
        "tags": ["bestiary", "虫豸", "水生", "异灵"],
        "content": """灰棘鱼是中域河流里最常见的异灵——巴掌大，灰绿色，背上有一排棘刺。棘刺含微量灵能毒素——被扎了手指肿半天，不致命但疼。灰棘鱼不是猎手——它们吃河底的灵能残渣和微生物。渔民最恨灰棘鱼——灰棘鱼多的河段其他鱼活不了，灵能毒素渗入河水，普通鱼死光了。灰棘鱼本身不能吃——灵能毒素积累在鱼肉里，吃了嘴唇发麻恶心半天。但灰棘鱼的棘刺磨粉可以做低级纹路墨的添加剂——增加墨线的灵能传导性。这是外围纹路师的小窍门，行会不认证但管用。"""
    },
]

# ═══════════════════════════════════════════════════════════════
# PART 4: 建筑重命名 + 重新设计
# ═══════════════════════════════════════════════════════════════

# 建筑重命名方案——拒绝管道风格，按中世纪+灵能黑科技世界观设计
BUILDING_RENAME = [
    ("building", "纹路白塔城", "枢城", "内城不是'白塔堆',是灵枢核心城;'枢'出自庄子天枢,有权力中心感;民间叫'内城'"),
    ("building", "纹路砖城", "灰城", "中域城墙灰白色;'灰城'朴素但有力;比'纹路砖城'有中世纪质感"),
    ("building", "纹路工坊区", "锻区", "'锻'=锻造;中世纪工匠区就叫'锻区';不说'纹路工坊'"),
]

# ═══════════════════════════════════════════════════════════════
# PART 5: 纪元历史修正
# ═══════════════════════════════════════════════════════════════

ERA2_CONTENT = """纪元2的核心事件是兽潮——灵能催生妖物大规模进化，兽潮频发，人类陷入生死存亡的战争。教会正是在兽潮中诞生的——不是谁刻意创建了教会，是绝望中的人类自发聚集在那些能对抗兽潮的觉醒者身边，把他们当作救世主。当救世主变成了信仰，教会就自然形成了。

纪元2最惨烈的事件是一次历史罕见的超级兽潮。灵能浓度在短时间内加速扩散——不是缓慢上升，是像洪水决堤一样暴涨。研究院后来的推算认为，那次兽潮导致灵能浓度扩散速度比正常快了十倍。兽潮从四面八方同时涌来，规模大到连壁盾军团的前身都无法同时防守。

裴昭和裴晗就是在这场超级兽潮中牺牲的。裴昭是当时最强的觉醒者之一，他选择把自己铸成灵能容器——不是被迫，是在所有人都要死的时候，他说"用我吧"。灵能容器在战场上展开，形成一个巨大的灵能屏障，挡住了兽潮的主攻方向。但裴晗——他的妹妹——没有退到屏障后面。她在侧翼独自抵挡从另一个方向涌来的妖物群，给平民争取撤退时间。等裴昭在屏障里意识到妹妹不在身后的时候，已经晚了。他什么都做不了——灵能容器的结构不允许他移动。他只能感觉到妹妹的灵能信号一点一点变弱，最后消失。

裴昭在灵能容器里活了下来。但他的妹妹死了，他的自由没了，他把自己关在了一个他亲手设计的牢笼里。"属下还能为您效忠"——这句话不只是对虞渊说的，是对自己说的。每次重复，都是在告诉自己：你还活着，所以你还得撑着。

教会在这次超级兽潮之后迅速壮大。人们需要相信有什么东西在保护他们——灵能容器是看不见的，但教会是看得见的。教会把裴昭的事迹改编成了教义中的"圣者献身"，把灵能容器的灵能波动说成是永恒者的庇护。虞渊默许了——信仰等于秩序，秩序等于控制。

灵站在纪元2初被建立时，有三重善意功能：压制渊（抽取环境灵能降低浓度让渊不苏醒）、治疗灵衰（引渡椅向患者注入微量灵能镇定散稳定回路缓解症状）、经济互助（患者留下灵晶=治疗费+收入，治病不花钱还能赚钱）。灵站在原始设计中=恒温器+医院+救济站。"""

ERA3_CONTENT = """纪元3的核心转折是灵纹革命。两个天才——许知和许行——发现了一个改变一切的秘密：灵纹+特殊物品可以触发各种能力。

这不是凭空发现的。许知和许行在第三纪元遗迹中研究了多年，他们发现遗迹中的灵纹不是装饰——是功能性的。灵纹是灵能的"编程语言"，特定图案引导灵能特定流动，产生特定效果。而灵纹需要载体——不是任何材料都行，只有特定的灵矿石、骨材、灵晶纤维等"特殊物品"才能承载灵纹的灵能回路。

许知和许行的贡献不是发明灵纹——灵纹是第三纪元文明已经掌握的技术。他们的贡献是逆向工程：从遗迹遗纹中破译灵纹的原理，然后重新设计适合当前人类使用的灵纹体系。他们把远古的复杂纹路简化为人类可以理解和刻印的标准纹路——单纹、叠纹、阵纹，三级递进。这就是后世纹路体系的源头。

灵纹革命让人类在对抗异灵的战争中取得了阶段性胜利。有了纹路武器、纹路防御、纹路通讯，普通人也能通过灵能装备获得战斗力。壁盾军团从一支靠人命堆的防守队变成了一支有体系装备的军事力量。猎人从只敢猎杀虫豸变成了能猎杀牙甚至角级的专业团队。

但阶段性胜利带来了新的问题——很多人不满教会的统治。教会垄断碑文解读权、控制信息流通、压迫异见者，这些在兽潮时期是"必要的牺牲"，在胜利时期就变成了"不可容忍的压迫"。各地的反抗势力开始冒头，有人质疑教会的教义，有人拒绝缴纳教会什一税，有人公开宣称"永恒者"是编出来的。

内乱爆发了。反抗教会的人不是坏人——他们是真的受够了。但内乱不只针对教会，还针对灵枢。灵枢的灵站体系被认为是在"吸血"，纹路师行会的认证制度被认为是在"垄断知识"。两个天才许知和许行被卷入了内乱的漩涡——各方势力都想争取他们的灵纹技术，或者阻止对方获得它。

许知和许行最终死于内乱。不是被哪一方杀的——是在各方势力的拉扯中，他们成了所有人眼中的棋子。他们试图保持中立，但中立在内乱中等于同时得罪所有人。许知在保护自己的研究资料时被一支反抗军误杀，许行在试图为哥哥收尸时被教会裁判官以"通敌"罪名处决。

虞渊看到了这一切。纪元3的内乱和纪元2的兽潮，让虞渊做出了最终决定——他选择了现在的路线：一边控制灵能浓度防止渊醒来，一边让人类和异灵相互消耗，避免任何一方做大导致历史重演。

他不是冷血。他见过纪元2兽潮差点灭绝人类，也见过纪元3内乱差点撕裂文明。两个极端他都不想再看到。所以他选择了中间路线——不是最好的方案，是两边都伤但不死的方案。

许知许行留下的公式墙在V8双星城废墟中被发现，上面有灵衰症治疗所需的清淤方程——林原的清除方案加上许知许行的方程，才凑成一套完整的清除技术。

灵枢在纪元3末进行了第一次"优化"：不同体质产灵晶率不同——"高产出源"标记诞生。标记后吸收强度上调20%，稳定剂减量10%，产出率+50%。运营部对核心层汇报的总量数字正常——虞渊不知道。这就是"平庸之恶"的开端。"""


# ═══════════════════════════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════════════════════════

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    renamed = []
    errors = []

    def rename_entry(category, old_name, new_name, rationale):
        """Rename a world_settings entry"""
        try:
            # Check if old exists
            cur.execute(
                "SELECT id, data, keys, secondary_keys, tags FROM world_settings WHERE novel_id=? AND category=? AND name=?",
                (NOVEL_ID, category, old_name)
            )
            row = cur.fetchone()
            if not row:
                print(f"  ⚠️ NOT FOUND: {category}:{old_name}")
                errors.append(f"NOT FOUND: {category}:{old_name}")
                return

            # Update name
            cur.execute(
                "UPDATE world_settings SET name=?, updated_at=CURRENT_TIMESTAMP WHERE novel_id=? AND category=? AND name=?",
                (new_name, NOVEL_ID, category, old_name)
            )
            renamed.append(f"{category}: {old_name} → {new_name} ({rationale})")
            print(f"  ✅ {category}: {old_name} → {new_name}")
        except Exception as e:
            errors.append(f"ERROR renaming {category}:{old_name}: {e}")
            print(f"  ❌ ERROR: {category}:{old_name}: {e}")

    def update_content(category, name, new_content):
        """Update the content field of a world_settings entry"""
        try:
            cur.execute(
                "SELECT id, data FROM world_settings WHERE novel_id=? AND category=? AND name=?",
                (NOVEL_ID, category, name)
            )
            row = cur.fetchone()
            if not row:
                print(f"  ⚠️ NOT FOUND: {category}:{name}")
                return

            data = row['data']
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    data = {"content": data}

            data['content'] = new_content
            data_json = json.dumps(data, ensure_ascii=False)

            cur.execute(
                "UPDATE world_settings SET data=?, updated_at=CURRENT_TIMESTAMP WHERE novel_id=? AND category=? AND name=?",
                (data_json, NOVEL_ID, category, name)
            )
            print(f"  ✅ Updated content: {category}:{name}")
        except Exception as e:
            errors.append(f"ERROR updating content {category}:{name}: {e}")
            print(f"  ❌ ERROR updating content: {category}:{name}: {e}")

    def add_entry(category, name, keys, secondary_keys, tags, content, priority=30):
        """Add a new world_settings entry"""
        data = {"content": content}
        data_json = json.dumps(data, ensure_ascii=False)
        keys_json = json.dumps(keys, ensure_ascii=False)
        sec_keys_json = json.dumps(secondary_keys, ensure_ascii=False)
        tags_json = json.dumps(tags, ensure_ascii=False)

        try:
            cur.execute(
                "INSERT OR REPLACE INTO world_settings (novel_id, category, name, data, keys, secondary_keys, tags, priority, is_constant, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (NOVEL_ID, category, name, data_json, keys_json, sec_keys_json, tags_json, priority)
            )
            print(f"  ✅ Added: {category}:{name}")
        except Exception as e:
            errors.append(f"ERROR adding {category}:{name}: {e}")
            print(f"  ❌ ERROR adding: {category}:{name}: {e}")

    # ── Step 1: Rename entries ──
    print("\n═══ STEP 1: 重命名 (ability/bestiary/building/plant/daily/economy/core_setting) ═══")
    for cat, old, new, reason in RENAME_PLAN:
        rename_entry(cat, old, new, reason)

    print("\n═══ STEP 1b: 重命名 (item类——去除'纹路'前缀) ═══")
    for cat, old, new, reason in ITEM_RENAME:
        rename_entry(cat, old, new, reason)

    print("\n═══ STEP 1c: 重命名 (building类) ═══")
    for cat, old, new, reason in BUILDING_RENAME:
        rename_entry(cat, old, new, reason)

    # ── Step 2: Update Era history ──
    print("\n═══ STEP 2: 修正纪元历史 ═══")
    update_content("history", "纪元2·战火", ERA2_CONTENT)
    update_content("history", "纪元3·秩序", ERA3_CONTENT)

    # Also update the overview table in 纪元概览
    cur.execute(
        "SELECT data FROM world_settings WHERE novel_id=? AND category='history' AND name='纪元概览'",
        (NOVEL_ID,)
    )
    row = cur.fetchone()
    if row:
        data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
        data['content'] = """| 纪元 | 时间 | 关键人物 | 核心事件 | 虞渊管理迭代 | 主角团对应 |
|------|------|---------|---------|-------------|-----------|
| 1 起源 | ~400年前 | 封绝+虞渊 | 封印泄漏灵能弥漫，第一批人觉醒。封绝选择封印，虞渊选择控制 | 无管理。灵能自由弥漫，觉醒者不可控 | 陆沉+虞渊 |
| 2 战火 | ~300年前 | 裴昭+裴晗 | 兽潮频发，教会因此诞生。超级兽潮灵能浓度加速扩散，裴昭铸为灵能容器，裴晗战死。虞渊初版控制灵能浓度失败 | 初版：控制灵能浓度。失败——觉醒者少了但妖物更多 | 江屿 |
| 3 秩序 | ~100多年前 | 许知+许行 | 许知许行发现灵纹+特殊物品触发能力，灵纹革命让人类取得阶段性胜利。但不满教会统治引发内乱，两天才在内乱中死亡。虞渊决定双向消耗维持平衡 | 成熟模式：控制浓度+灵纹科技+双向消耗+阶级分化 | 汐 |
| 4 暗涌 | 当前 | 沈野+全队 | 灵能增长跟不上消耗。普通人被迫加速灵晶产出。妖物取晶+人类取晶→死循环 | 透支模式：榨取普通人+猎杀妖物。上一步维持不住了 | 沈野+全队 |

虞渊的管理模式不是一开始就这样。每一步都是"上一步不够用了"的结果。纪元2兽潮让虞渊选择控制，纪元3内乱让虞渊选择平衡。"""
        cur.execute(
            "UPDATE world_settings SET data=?, updated_at=CURRENT_TIMESTAMP WHERE novel_id=? AND category='history' AND name='纪元概览'",
            (json.dumps(data, ensure_ascii=False), NOVEL_ID)
        )
        print("  ✅ Updated 纪元概览")

    # ── Step 3: Add new plants ──
    print("\n═══ STEP 3: 新增灵能变异植物 ═══")
    for p in NEW_PLANTS:
        add_entry("plant", p["name"], p["keys"], p["secondary_keys"], p["tags"], p["content"])

    # ── Step 4: Add new beasts ──
    print("\n═══ STEP 4: 新增异灵/兽类 ═══")
    for b in NEW_BEASTS:
        add_entry("bestiary", b["name"], b["keys"], b["secondary_keys"], b["tags"], b["content"])

    # ── Step 5: Update 术语规范 to include naming rules ──
    print("\n═══ STEP 5: 更新术语规范 ═══")
    cur.execute(
        "SELECT id FROM world_settings WHERE novel_id=? AND category='core_setting' AND name='术语规范'",
        (NOVEL_ID,)
    )
    if cur.fetchone():
        # Update existing
        pass  # 术语规范 is in a separate md file, not in world_settings
    print("  ℹ️ 术语规范在独立md文件中，需单独更新")

    conn.commit()

    # ── Summary ──
    print("\n═══ 执行总结 ═══")
    print(f"重命名: {len(renamed)} 条")
    for r in renamed:
        print(f"  {r}")
    print(f"新增植物: {len(NEW_PLANTS)} 条")
    print(f"新增异灵: {len(NEW_BEASTS)} 条")
    if errors:
        print(f"错误: {len(errors)} 条")
        for e in errors:
            print(f"  {e}")

    # ── Final audit: count remaining "灵" issues ──
    cur.execute("SELECT category, name FROM world_settings WHERE novel_id=? AND name LIKE '%灵能%'", (NOVEL_ID,))
    remaining = cur.fetchall()
    if remaining:
        print(f"\n⚠️ 仍含'灵能'前缀的条目: {len(remaining)}")
        for r in remaining:
            print(f"  {r['category']}:{r['name']}")
    else:
        print("\n✅ 无'灵能'前缀残留")

    cur.execute("SELECT category, name FROM world_settings WHERE novel_id=? AND name LIKE '%纹路%'", (NOVEL_ID,))
    remaining = cur.fetchall()
    if remaining:
        print(f"\n⚠️ 仍含'纹路'前缀的条目: {len(remaining)}")
        for r in remaining:
            print(f"  {r['category']}:{r['name']}")
    else:
        print("✅ 无'纹路'前缀残留")

    conn.close()
    print("\n✅ 数据库更新完成!")


if __name__ == "__main__":
    main()
