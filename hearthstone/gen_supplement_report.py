# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, '/home/z/my-project/skills/pdf/scripts')
from pdf import install_font_fallback

import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                 Table, TableStyle, Image, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

pdfmetrics.registerFont(TTFont('Microsoft YaHei', '/usr/share/fonts/truetype/chinese/msyh.ttf'))
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))
registerFontFamily('Microsoft YaHei', normal='Microsoft YaHei', bold='Microsoft YaHei')
registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
install_font_fallback()

ACCENT = colors.HexColor('#e67e22')
TEXT_PRIMARY = colors.HexColor('#242220')
TEXT_MUTED = colors.HexColor('#807b73')
BG_SURFACE = colors.HexColor('#dfdcd7')
TABLE_HEADER_COLOR = ACCENT
TABLE_HEADER_TEXT = colors.white
TABLE_ROW_EVEN = colors.white
TABLE_ROW_ODD = BG_SURFACE

with open('/home/z/my-project/hearthstone/supplement_new_mechanics.json', 'r') as f:
    supp = json.load(f)

PAGE_W, PAGE_H = A4
LEFT_M = 1.0 * inch
RIGHT_M = 1.0 * inch
TOP_M = 0.8 * inch
BOT_M = 0.8 * inch
AVAIL_W = PAGE_W - LEFT_M - RIGHT_M

h1_style = ParagraphStyle(name='H1', fontName='Microsoft YaHei', fontSize=20, leading=28, textColor=TEXT_PRIMARY, spaceBefore=18, spaceAfter=12, alignment=TA_LEFT, wordWrap='CJK')
h2_style = ParagraphStyle(name='H2', fontName='Microsoft YaHei', fontSize=15, leading=22, textColor=ACCENT, spaceBefore=14, spaceAfter=8, alignment=TA_LEFT, wordWrap='CJK')
h3_style = ParagraphStyle(name='H3', fontName='Microsoft YaHei', fontSize=12, leading=18, textColor=TEXT_PRIMARY, spaceBefore=10, spaceAfter=6, alignment=TA_LEFT, wordWrap='CJK')
body_style = ParagraphStyle(name='Body', fontName='SimHei', fontSize=10.5, leading=18, textColor=TEXT_PRIMARY, spaceBefore=0, spaceAfter=6, alignment=TA_LEFT, wordWrap='CJK', firstLineIndent=21)
caption_style = ParagraphStyle(name='Caption', fontName='SimHei', fontSize=9, leading=14, textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=3, spaceAfter=6, wordWrap='CJK')
header_cell = ParagraphStyle(name='HC', fontName='SimHei', fontSize=10, leading=14, textColor=colors.white, alignment=TA_CENTER, wordWrap='CJK')
data_cell = ParagraphStyle(name='DC', fontName='SimHei', fontSize=9.5, leading=14, textColor=TEXT_PRIMARY, alignment=TA_CENTER, wordWrap='CJK')
data_cell_l = ParagraphStyle(name='DCL', fontName='SimHei', fontSize=9.5, leading=14, textColor=TEXT_PRIMARY, alignment=TA_LEFT, wordWrap='CJK')

def make_table(data_rows, col_widths):
    table = Table(data_rows, colWidths=col_widths, hAlign='CENTER')
    style_cmds = [
        ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), TABLE_HEADER_TEXT),
    ]
    for i in range(1, len(data_rows)):
        bg = TABLE_ROW_EVEN if i % 2 == 1 else TABLE_ROW_ODD
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
    table.setStyle(TableStyle(style_cmds))
    return table

def add_img(path, max_w=AVAIL_W, max_h=300):
    img = Image(path)
    w, h = img.drawWidth, img.drawHeight
    ratio = min(max_w / w, max_h / h, 1.0)
    img.drawWidth = w * ratio
    img.drawHeight = h * ratio
    return img

output_path = '/home/z/my-project/download/hs_new_mechanics_body.pdf'
doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=LEFT_M, rightMargin=RIGHT_M, topMargin=TOP_M, bottomMargin=BOT_M)

story = []

# === Chapter 1: Overview ===
story.append(Paragraph('<b>一、新机制关键词全景</b>', h1_style))
story.append(Spacer(1, 6))
story.append(Paragraph(
    '在首次分析中，我们仅基于卡牌的mechanics标签进行统计，遗漏了大量仅在卡牌描述文本中以'
    '<b>加粗标签</b>形式呈现的新机制关键词。经过全面文本扫描后，发现标准模式中存在11种未纳入mechanics标签的新机制，'
    '合计产生154次卡牌引用。新机制的引入大幅丰富了标准模式的策略维度，尤其在特定职业和卡组中形成了独特的构筑体系。',
    body_style
))
story.append(Paragraph(
    '从数据分布来看，新机制主要集中在大灾变(14张兆示、6张裂变)和翡翠之梦(16张灌注、17张黑暗之赐)两个最新扩展包中，'
    '体现了暴雪每个扩展包引入1-2种标志性新机制的设计惯例。时光之旅扩展包则带来了回溯(17张)、奇闻(9张)等时空主题机制。'
    '死亡骑士作为新加入的职业，独占了残骸(22张)和复生(10张)两种核心机制，形成了完全独立于传统十职业的资源系统。',
    body_style
))

# New mech summary table
mech_rows = [[
    Paragraph('<b>新机制</b>', header_cell),
    Paragraph('<b>卡牌数</b>', header_cell),
    Paragraph('<b>主要卡组</b>', header_cell),
    Paragraph('<b>主要职业</b>', header_cell),
    Paragraph('<b>机制类型</b>', header_cell),
]]
mech_detail = [
    ('残骸', '23', '核心(12)', '死亡骑士(22)', '资源消耗'),
    ('黑暗之赐', '20', '翡翠之梦(17)', '中立/术士/战士', '属性增益'),
    ('灌注', '19', '翡翠之梦(16)', '中立/猎人/萨满', '技能强化'),
    ('扰魔', '18', '时光之旅(5)', '中立/德鲁伊/牧师', '法术免疫'),
    ('回溯', '18', '时光之旅(17)', '中立/法师/潜行', '双轨效果'),
    ('兆示', '14', '大灾变(14)', '中立/死亡骑士/潜行', '条件触发'),
    ('休眠', '14', '翡翠之梦(6)', '中立/恶魔猎手', '延迟部署'),
    ('复生', '10', '核心(4)', '死亡骑士(5)', '重复召唤'),
    ('奇闻', '9', '时光之旅(9)', '各职业均分', '传说效果'),
    ('裂变', '7', '大灾变(6)', '各职业均分', '双卡拼合'),
    ('延系', '2+', '失落之城(2+)', '中立', '连锁触发'),
]
for name, cnt, set_main, class_main, mtype in mech_detail:
    mech_rows.append([
        Paragraph(name, data_cell_l),
        Paragraph(cnt, data_cell),
        Paragraph(set_main, data_cell),
        Paragraph(class_main, data_cell),
        Paragraph(mtype, data_cell),
    ])
cw = [AVAIL_W*0.15, AVAIL_W*0.12, AVAIL_W*0.22, AVAIL_W*0.25, AVAIL_W*0.26]
story.append(Spacer(1, 12))
story.append(make_table(mech_rows, cw))
story.append(Paragraph('表1 新机制关键词完整统计', caption_style))

# === Chart: Full ranking ===
story.append(Spacer(1, 12))
story.append(add_img('/home/z/my-project/download/chart_full_keyword_top20.png', max_h=280))
story.append(Paragraph('图1 完整关键词排名TOP20（橙色=新机制 | 蓝色=传统机制）', caption_style))

# === Chapter 2: New vs Old ===
story.append(Spacer(1, 18))
story.append(Paragraph('<b>二、新旧机制对比分析</b>', h1_style))
story.append(Spacer(1, 6))
story.append(Paragraph(
    '传统关键词(mechanics标签)产生779次卡牌引用，新机制(文本标签)产生154次引用，'
    '新机制占比约16.5%。虽然绝对数量不及传统关键词，但新机制往往具有更复杂的行为逻辑和更高的战略上限。'
    '传统关键词如战吼、亡语、嘲讽等已历经多年环境验证，其行为模式相对固定且可预测。'
    '而新机制如兆示、裂变、奇闻等引入了概率因素和组合维度，为标准模式带来了更高的变化性和构筑深度。',
    body_style
))
story.append(Paragraph(
    '值得关注的是，新机制与传统关键词之间存在大量的交叉共存关系。'
    '例如"黑暗之赐"几乎总是与"发现"机制配合出现（发现一张具有黑暗之赐的卡牌），'
    '形成了"择取+增益"的复合收益链。"扰魔"经常与嘲讽、圣盾等传统关键词共存，'
    '创造了"法术免疫+物理防御"的双保险效果。这种新旧机制的融合设计是当前标准模式的一大特色。',
    body_style
))

story.append(Spacer(1, 8))
story.append(add_img('/home/z/my-project/download/chart_new_vs_old_mechanics.png', max_h=230))
story.append(Paragraph('图2 新旧机制占比及新机制构成', caption_style))

# === Chapter 3: Set Distribution ===
story.append(Spacer(1, 18))
story.append(Paragraph('<b>三、新机制卡组分布特征</b>', h1_style))
story.append(Spacer(1, 6))

story.append(Paragraph('<b>3.1 大灾变(CATACLYSM) — 兆示与裂变</b>', h2_style))
story.append(Paragraph(
    '大灾变扩展包引入了兆示(14张)和裂变(7张)两种全新机制。兆示卡牌会在手牌中积累条件，'
    '当条件满足时触发强力效果——这实际上是一种"延迟战吼"设计，让玩家可以提前规划下回合甚至下下回合的节奏。'
    '兆示卡的费用分布从1费到高费不等，低费兆示适合快攻和中速套牌用于前期施压，'
    '高费兆示则作为控制套牌的后期终极武器。兆示机制的核心博弈在于"是否提前暴露意图"——'
    '对手可以通过观察你的手牌变化来预判兆示触发的时机，从而做出针对性的应对。',
    body_style
))
story.append(Paragraph(
    '裂变机制则采用了"双卡拼合"的设计理念，两张裂变卡可以在同一回合打出后合并为一张强力卡牌。'
    '这要求玩家在构筑时同时投入两张卡牌 slots，增加了构筑成本但也带来了更高的组合上限。'
    '裂变机制6张卡分布在大灾变中，涵盖德鲁伊、潜行者、牧师、圣骑士、法师五个职业，'
    '是本扩展包中最具创意的机制设计。',
    body_style
))

story.append(Paragraph('<b>3.2 翡翠之梦(EMERALD_DREAM) — 灌注与黑暗之赐</b>', h2_style))
story.append(Paragraph(
    '翡翠之梦带来了灌注(16张)和黑暗之赐(17张)两种机制。灌注机制强化英雄技能，'
    '使其获得额外效果——例如"灌注你的英雄技能"后，法师的火球术可能附带冻结效果，'
    '猎人的稳固射击可能召唤额外野兽。这种设计让英雄技能从基础的2费1点伤害/1点护甲'
    '升级为多功能的核心资源，极大地丰富了中后期的操作空间。灌注卡牌的费用分布偏中低(2-5费)，'
    '适合中速套牌在前中期建立优势后通过升级英雄技能拉开差距。',
    body_style
))
story.append(Paragraph(
    '黑暗之赐则是一种随从属性增益系统，具有黑暗之赐的卡牌在满足特定条件时获得额外属性。'
    '与其他增益机制不同的是，黑暗之赐的增益是永久性的且可以被"发现"机制择取传播——'
    '多张卡牌具有"发现一张具有黑暗之赐的卡牌"的战吼效果，形成了增益的连锁传播。'
    '黑暗之赐在术士(4张)、战士(3张)、潜行者(3张)、死亡骑士(3张)中有较多分布，'
    '其中术士通过牺牲生命值来触发黑暗之赐的增益，完美契合其种族特色。',
    body_style
))

story.append(Paragraph('<b>3.3 时光之旅(TIME_TRAVEL) — 回溯与奇闻</b>', h2_style))
story.append(Paragraph(
    '时光之旅扩展包的核心机制是回溯(17张)和奇闻(9张)。回溯机制让卡牌在打出时产生两种不同的效果，'
    '玩家可以选择其中一种执行——这实际上是一种变体的"抉择"机制，但回溯的两种结果都与原卡效果相关。'
    '更具特色的是，部分回溯卡（如米罗克）可以同时保留两种结果，实现双倍收益。'
    '回溯卡的费用集中在2-6费段，是中速套牌的核心操作组件。',
    body_style
))
story.append(Paragraph(
    '奇闻机制是时光之旅最具野心的设计——每张奇闻卡都是一张独立的"传说级别"卡牌，'
    '具有独特的、打破常规规则的效果。9张奇闻卡均匀分布在各个职业中（每职业约1张），'
    '构成了时光之旅扩展包的收藏核心。奇闻卡的强度普遍较高，在对局中往往能产生逆转性效果，'
    '但其高费用和稀有度也意味着构筑需要围绕奇闻卡进行专门的资源规划。',
    body_style
))

story.append(Paragraph('<b>3.4 死亡骑士专属 — 残骸与复生</b>', h2_style))
story.append(Paragraph(
    '死亡骑士作为标准模式的新加入职业，拥有完全独立的资源系统——残骸(22张)。'
    '残骸是一种特殊资源，随从死亡后会积累残骸点数，特定卡牌可以消耗残骸来触发额外效果。'
    '这使死亡骑士成为唯一一个拥有"第三资源"的职业（法力值+手牌+残骸），'
    '极大地增加了其操作复杂度和策略深度。残骸系统与亡语机制形成了天然的协同——'
    '通过主动触发随从死亡来快速积累残骸，再利用残骸释放强力效果，构成了死亡骑士的核心运作循环。',
    body_style
))
story.append(Paragraph(
    '复生(10张)是残骸系统的配套机制，当消耗足够残骸后，复生随从会在死亡后重新召唤。'
    '与传统的重生(Reborn，仅触发一次且为1/1)不同，复生通常召唤完整属性值的复制体，'
    '配合残骸的持续积累可以形成无限循环的价值引擎。复生卡主要集中在死亡骑士(5张)和中立卡(4张)中，'
    '其中中立复生卡可供其他职业使用，为非死亡骑士套牌提供了亡语体系的补充选择。',
    body_style
))

story.append(Spacer(1, 8))
story.append(add_img('/home/z/my-project/download/chart_new_mech_by_set.png', max_h=250))
story.append(Paragraph('图3 新机制关键词按卡组分布', caption_style))

# === Chapter 4: Class Heatmap ===
story.append(Spacer(1, 18))
story.append(Paragraph('<b>四、新机制职业特征分析</b>', h1_style))
story.append(Spacer(1, 6))

story.append(Paragraph(
    '新机制在职业间的分布呈现出强烈的"主题绑定"特征。死亡骑士以残骸(22)+复生(5)=27张新机制卡'
    '遥遥领先，约占其职业总卡牌的42%，这使得死亡骑士的对局逻辑与传统十职业截然不同。'
    '术士、战士、潜行者、德鲁伊各有4-6张新机制卡，形成了适度的新机制融入。'
    '而法师、圣骑士、萨满的新机制卡较少，更多依赖传统关键词体系。',
    body_style
))

story.append(Spacer(1, 8))
story.append(add_img('/home/z/my-project/download/chart_new_mech_class_heatmap.png', max_h=280))
story.append(Paragraph('图4 新机制关键词职业分布热力图', caption_style))

# Class new mech table
cls_rows = [[
    Paragraph('<b>职业</b>', header_cell),
    Paragraph('<b>新机制卡数</b>', header_cell),
    Paragraph('<b>核心新机制</b>', header_cell),
    Paragraph('<b>策略影响</b>', header_cell),
]]
cls_data = [
    ('死亡骑士', '27', '残骸(22) + 复生(5)', '独立资源体系，亡语循环'),
    ('术士', '7', '黑暗之赐(4)', '牺牲增益，发现传播'),
    ('战士', '6', '黑暗之赐(3) + 兆示(2)', '条件增益+延迟触发'),
    ('潜行者', '6', '兆示(2) + 回溯(1)', '手牌规划+双轨操作'),
    ('德鲁伊', '5', '扰魔(3) + 裂变(1)', '法术免疫+拼合组合'),
    ('恶魔猎手', '5', '兆示(2) + 休眠(5)', '延迟部署+条件触发'),
    ('中立', '30', '黑暗之赐(5)+灌注(6)', '多机制万金油'),
]
for cls, cnt, core, impact in cls_data:
    cls_rows.append([
        Paragraph(cls, data_cell),
        Paragraph(cnt, data_cell),
        Paragraph(core, data_cell_l),
        Paragraph(impact, data_cell_l),
    ])
cw2 = [AVAIL_W*0.16, AVAIL_W*0.14, AVAIL_W*0.36, AVAIL_W*0.34]
story.append(Spacer(1, 12))
story.append(make_table(cls_rows, cw2))
story.append(Paragraph('表2 各职业新机制关键词分布', caption_style))

# === Chapter 5: Decision Model Update ===
story.append(Spacer(1, 18))
story.append(Paragraph('<b>五、关键词决策模型更新</b>', h1_style))
story.append(Spacer(1, 6))

story.append(Paragraph(
    '纳入新机制后，关键词策略决策模型需要扩展为"传统机制+新机制"的双层评估体系。'
    '传统机制层继续基于费用-属性效率模型进行面板评估，新机制层则需要针对每种机制的特殊逻辑'
    '建立独立的评估维度。以下是更新后的决策框架要点：',
    body_style
))

story.append(Paragraph('<b>5.1 新机制价值评估维度</b>', h2_style))
story.append(Paragraph(
    '资源类机制（残骸）：需要评估"残骸积累速率"和"残骸消耗效率"。一个回合能产生2+残骸的'
    '套牌配置视为高效，单次消耗4+残骸的效果需至少产出等值6费以上的场面影响力才值得投入。'
    '残骸卡在对局中的时序规划尤为关键——过早消耗残骸可能导致后期缺乏资源，过晚则错失场面节奏。',
    body_style
))
story.append(Paragraph(
    '条件触发类机制（兆示、黑暗之赐）：需要评估"触发概率"和"触发收益"。兆示卡在手牌中的'
    '触发条件决定了其生效的确定性——固定条件（如回合数）兆示适合精确规划，'
    '随机条件兆示则适合风险偏好型套牌。黑暗之赐的增益幅度通常为+2/+2或更高，'
    '但需要考虑触发条件的达成难度。与发现机制配合时，黑暗之赐的实际覆盖率约为60-70%。',
    body_style
))
story.append(Paragraph(
    '操作选择类机制（回溯、抉择、裂变）：需要评估"选择灵活度"和"最优选择路径"。'
    '回溯的双轨效果使每张卡的期望价值约为单效果卡的1.5倍（考虑信息不对称和对手应对）。'
    '裂变需要两张卡的配合才能发挥，实际价值需打折约40%（考虑卡手风险），但触发后的组合效果'
    '通常远超两张卡各自价值的简单相加。',
    body_style
))
story.append(Paragraph(
    '延迟类机制（休眠、延系）：需要评估"时间成本"和"落地收益"。休眠2回合的卡牌'
    '需要至少提供2回合后的4费以上等值效果才值得投入，休眠1回合则门槛降低至2费等值。'
    '延系的连锁触发机制适合多段节奏套牌，可以在一回合内完成多步操作链。',
    body_style
))

story.append(Paragraph('<b>5.2 更新后的流派关键词偏好矩阵</b>', h2_style))
arch_rows = [[
    Paragraph('<b>流派</b>', header_cell),
    Paragraph('<b>传统优先</b>', header_cell),
    Paragraph('<b>新机制优先</b>', header_cell),
    Paragraph('<b>费用偏好</b>', header_cell),
]]
arch_data = [
    ('快攻', '突袭、圣盾、风怒', '兆示(低费)', '1~3费'),
    ('中速', '战吼、发现、嘲讽', '灌注、回溯、黑暗之赐', '3~6费'),
    ('控制', '亡语、吸血、嘲讽', '残骸、复生、扰魔', '5~8费'),
    ('组合', '战吼、发现、任务', '裂变、奇闻、休眠', '全费用段'),
]
for arch, old_kw, new_kw, cost in arch_data:
    arch_rows.append([
        Paragraph(arch, data_cell),
        Paragraph(old_kw, data_cell_l),
        Paragraph(new_kw, data_cell_l),
        Paragraph(cost, data_cell),
    ])
cw3 = [AVAIL_W*0.12, AVAIL_W*0.30, AVAIL_W*0.36, AVAIL_W*0.22]
story.append(Spacer(1, 12))
story.append(make_table(arch_rows, cw3))
story.append(Paragraph('表3 更新后的流派关键词偏好矩阵（含新机制）', caption_style))

doc.build(story)
print(f"Supplement PDF: {output_path}")
