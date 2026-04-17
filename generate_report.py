# -*- coding: utf-8 -*-
"""
炉石传说标准模式卡牌数据分析与对局抉择模型
"""
import os, sys
PDF_SKILL_DIR = "/home/z/my-project/skills/pdf"
_scripts = os.path.join(PDF_SKILL_DIR, "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)
from pdf import install_font_fallback

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether, CondPageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus.tableofcontents import TableOfContents
import hashlib

# ━━ Font Registration ━━
pdfmetrics.registerFont(TTFont('Microsoft YaHei', '/usr/share/fonts/truetype/chinese/msyh.ttf'))
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
registerFontFamily('Microsoft YaHei', normal='Microsoft YaHei', bold='Microsoft YaHei')
registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')
registerFontFamily('DejaVuSans', normal='DejaVuSans', bold='DejaVuSans')
install_font_fallback()

# ━━ Color Palette ━━
ACCENT       = colors.HexColor('#d82442')
TEXT_PRIMARY  = colors.HexColor('#242220')
TEXT_MUTED    = colors.HexColor('#79746d')
BG_SURFACE   = colors.HexColor('#e3e0da')
BG_PAGE      = colors.HexColor('#edecea')
TABLE_HEADER_COLOR = ACCENT
TABLE_HEADER_TEXT  = colors.white
TABLE_ROW_EVEN     = colors.white
TABLE_ROW_ODD      = BG_SURFACE

# ━━ Styles ━━
styles = {
    'Title': ParagraphStyle(
        name='Title', fontName='Microsoft YaHei', fontSize=24, leading=32,
        alignment=TA_CENTER, textColor=TEXT_PRIMARY, spaceAfter=12,
        wordWrap='CJK'
    ),
    'H1': ParagraphStyle(
        name='H1', fontName='Microsoft YaHei', fontSize=18, leading=26,
        textColor=TEXT_PRIMARY, spaceBefore=18, spaceAfter=10,
        wordWrap='CJK'
    ),
    'H2': ParagraphStyle(
        name='H2', fontName='Microsoft YaHei', fontSize=14, leading=20,
        textColor=ACCENT, spaceBefore=14, spaceAfter=8,
        wordWrap='CJK'
    ),
    'H3': ParagraphStyle(
        name='H3', fontName='SimHei', fontSize=12, leading=18,
        textColor=TEXT_PRIMARY, spaceBefore=10, spaceAfter=6,
        wordWrap='CJK'
    ),
    'Body': ParagraphStyle(
        name='Body', fontName='SimHei', fontSize=10.5, leading=18,
        alignment=TA_LEFT, textColor=TEXT_PRIMARY, firstLineIndent=21,
        wordWrap='CJK', spaceBefore=0, spaceAfter=4,
    ),
    'BodyNoIndent': ParagraphStyle(
        name='BodyNoIndent', fontName='SimHei', fontSize=10.5, leading=18,
        alignment=TA_LEFT, textColor=TEXT_PRIMARY,
        wordWrap='CJK', spaceBefore=0, spaceAfter=4,
    ),
    'Formula': ParagraphStyle(
        name='Formula', fontName='SimHei', fontSize=11, leading=20,
        alignment=TA_CENTER, textColor=ACCENT, spaceBefore=8, spaceAfter=8,
        backColor=colors.HexColor('#fdf2f4'),
        borderPadding=8,
        wordWrap='CJK',
    ),
    'Caption': ParagraphStyle(
        name='Caption', fontName='SimHei', fontSize=9, leading=14,
        alignment=TA_CENTER, textColor=TEXT_MUTED, spaceBefore=3, spaceAfter=6,
        wordWrap='CJK',
    ),
    'TableHeader': ParagraphStyle(
        name='TableHeader', fontName='SimHei', fontSize=10,
        textColor=colors.white, alignment=TA_CENTER, wordWrap='CJK',
    ),
    'TableCell': ParagraphStyle(
        name='TableCell', fontName='SimHei', fontSize=9.5,
        textColor=TEXT_PRIMARY, alignment=TA_CENTER, wordWrap='CJK',
    ),
    'TableCellLeft': ParagraphStyle(
        name='TableCellLeft', fontName='SimHei', fontSize=9.5,
        textColor=TEXT_PRIMARY, alignment=TA_LEFT, wordWrap='CJK',
    ),
}

# ━━ TOC Support ━━
class TocDocTemplate(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if hasattr(flowable, 'bookmark_name'):
            level = getattr(flowable, 'bookmark_level', 0)
            text = getattr(flowable, 'bookmark_text', '')
            key = getattr(flowable, 'bookmark_key', '')
            self.notify('TOCEntry', (level, text, self.page, key))

def add_heading(text, style, level=0):
    key = 'h_%s' % hashlib.md5(text.encode()).hexdigest()[:8]
    p = Paragraph('<a name="%s"/>%s' % (key, text), style)
    p.bookmark_name = text
    p.bookmark_level = level
    p.bookmark_text = text.replace('<b>', '').replace('</b>', '')
    p.bookmark_key = key
    return p

available_height = A4[1] - 2*inch

def safe_keep_together(elements):
    total_h = 0
    for el in elements:
        w, h = el.wrap(A4[0] - 2*inch, A4[1])
        total_h += h
    if total_h <= available_height * 0.4:
        return [KeepTogether(elements)]
    elif len(elements) >= 2:
        return [KeepTogether(elements[:2])] + list(elements[2:])
    return list(elements)

# ━━ Build Document ━━
output_path = '/home/z/my-project/download/hearthstone_analysis_body.pdf'
doc = TocDocTemplate(
    output_path, pagesize=A4,
    leftMargin=1*inch, rightMargin=1*inch,
    topMargin=0.8*inch, bottomMargin=0.8*inch,
)

story = []

# ── TOC ──
story.append(Paragraph('<b>目录</b>', styles['Title']))
story.append(Spacer(1, 12))
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle(name='TOC1', fontName='SimHei', fontSize=12, leftIndent=20, spaceBefore=4, spaceAfter=2, wordWrap='CJK'),
    ParagraphStyle(name='TOC2', fontName='SimHei', fontSize=10.5, leftIndent=40, spaceBefore=2, spaceAfter=1, wordWrap='CJK'),
]
story.append(toc)
story.append(PageBreak())

# ═══════════════════════════════════════
# SECTION 1: 数据概览
# ═══════════════════════════════════════
story.append(add_heading('<b>一、标准模式数据概览</b>', styles['H1'], 0))

story.append(Paragraph(
    '本报告基于炉石传说"圣甲虫之年"（Year of the Scarab, 2026年3月起）标准模式卡牌数据，涵盖大灾变、穿越时空、失落之城、翡翠梦境四个扩展包，以及核心系列和活动卡组。数据来源为HearthstoneJSON API最新版本（中文），共计984张可收集卡牌。报告将围绕随从费用-属性数学模型、对局抉择收益模型、流派收益分析三大核心维度展开，旨在为玩家提供一套可量化的辅助决策工具。',
    styles['Body']
))

story.append(add_heading('<b>1.1 卡牌类型分布</b>', styles['H2'], 1))
story.append(Paragraph(
    '标准模式984张可收集卡牌中，随从（MINION）占据最大比例，共614张，占比约62.4%。法术（SPELL）紧随其后，共328张，占比33.3%。武器（WEAPON）仅有26张，地标（LOCATION）14张，英雄卡2张。随从和法术构成了标准模式的绝对主体，因此本报告的数学建模将重点围绕这两类卡牌展开，尤其是随从的攻击力与生命值属性。',
    styles['Body']
))

# Type distribution table
type_data = [
    [Paragraph('<b>卡牌类型</b>', styles['TableHeader']), Paragraph('<b>数量</b>', styles['TableHeader']), Paragraph('<b>占比</b>', styles['TableHeader'])],
    [Paragraph('随从', styles['TableCellLeft']), Paragraph('614', styles['TableCell']), Paragraph('62.4%', styles['TableCell'])],
    [Paragraph('法术', styles['TableCellLeft']), Paragraph('328', styles['TableCell']), Paragraph('33.3%', styles['TableCell'])],
    [Paragraph('武器', styles['TableCellLeft']), Paragraph('26', styles['TableCell']), Paragraph('2.6%', styles['TableCell'])],
    [Paragraph('地标', styles['TableCellLeft']), Paragraph('14', styles['TableCell']), Paragraph('1.4%', styles['TableCell'])],
    [Paragraph('英雄', styles['TableCellLeft']), Paragraph('2', styles['TableCell']), Paragraph('0.2%', styles['TableCell'])],
]
t = Table(type_data, colWidths=[150, 100, 100], hAlign='CENTER')
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR),
    ('TEXTCOLOR', (0, 0), (-1, 0), TABLE_HEADER_TEXT),
    ('BACKGROUND', (0, 1), (-1, 1), TABLE_ROW_EVEN),
    ('BACKGROUND', (0, 2), (-1, 2), TABLE_ROW_ODD),
    ('BACKGROUND', (0, 3), (-1, 3), TABLE_ROW_EVEN),
    ('BACKGROUND', (0, 4), (-1, 4), TABLE_ROW_ODD),
    ('BACKGROUND', (0, 5), (-1, 5), TABLE_ROW_EVEN),
    ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
]))
story.append(Spacer(1, 18))
story.append(t)
story.append(Paragraph('表1：标准模式卡牌类型分布', styles['Caption']))
story.append(Spacer(1, 18))

story.append(add_heading('<b>1.2 稀有度分布</b>', styles['H2'], 1))
story.append(Paragraph(
    '从稀有度分布来看，普通卡牌（COMMON）数量最多，达402张，占比40.9%，是构筑卡组的基础。稀有卡牌（RARE）260张，史诗卡牌（EPIC）和传说卡牌（LEGENDARY）各有159张和163张。需要注意的是，传说卡牌虽然数量不是最多，但由于构筑限制（同名传说卡只能携带一张），它们在卡组中的出现概率和影响力与其他稀有度有本质差异，这在后续的效率分析中需要特别考虑。',
    styles['Body']
))

# ═══════════════════════════════════════
# SECTION 2: 费用-属性数学模型
# ═══════════════════════════════════════
story.append(add_heading('<b>二、随从费用-属性数学模型</b>', styles['H1'], 0))

story.append(add_heading('<b>2.1 线性回归模型</b>', styles['H2'], 1))
story.append(Paragraph(
    '通过对613张有效随从卡牌（排除0费空属性卡牌和英雄卡）的法力值费用与总属性（攻击力+生命值）进行线性回归分析，我们得到了一个高显著性的线性模型。模型显示，在标准模式中，随从的期望总属性与法力值费用之间存在强正相关性，判定系数R平方值达到0.708，表明约70.8%的属性变异可以被费用差异所解释。这一比例相比全卡牌池（含狂野模式）有所降低，原因在于标准模式中存在更多带有特殊效果的"亏模"随从，它们以牺牲面板属性来换取战吼、亡语等附加价值。',
    styles['Body']
))

story.append(Paragraph('<b>期望总属性 = 1.53 x 费用 + 1.60</b>', styles['Formula']))
story.append(Paragraph('R平方 = 0.708, P值 < 0.001', styles['Caption']))

story.append(Paragraph(
    '该模型的含义十分直观：每增加1点法力值费用，随从的期望总属性增加约1.53点。截距1.60代表0费随从的基础属性期望值。基于此模型，我们可以定义"属性效率"指标：效率 = 实际总属性 / 期望总属性。效率大于1.0意味着该随从的面板超模，小于1.0则意味着亏模。当然，许多亏模随从的附加效果足以弥补面板的不足，因此效率指标应与其他因素综合考虑，而非孤立判断。',
    styles['Body']
))

# Chart 1
chart_dir = '/home/z/my-project/download/'
img1 = Image(chart_dir + 'chart1_cost_stats_model.png', width=440, height=256)
story.append(Spacer(1, 18))
story.append(img1)
story.append(Paragraph('图1：标准模式随从费用-属性散点图与线性回归模型', styles['Caption']))
story.append(Spacer(1, 18))

story.append(add_heading('<b>2.2 各费用段属性统计</b>', styles['H2'], 1))
story.append(Paragraph(
    '下表展示了每个费用段的平均属性值和效率关键阈值。高效率阈值（>1.1）意味着该费用段的优质随从应达到的总属性底线，而低效率阈值（<0.8）则标识了明显亏模的卡牌。从数据中可以发现，1费和2费随从的效率波动最大，这反映了低费随从在快攻与控制体系中的价值差异：快攻卡组极度依赖1-2费高效随从建立场面优势，而控制卡组则更关注高费随从的价值密度和生存能力。',
    styles['Body']
))

# Cost stats table
cost_data_rows = [
    ['1费', '3.13', '3.02', '3.44', '2.50', '55'],
    ['2费', '4.65', '4.72', '5.12', '3.72', '101'],
    ['3费', '6.18', '6.24', '6.80', '4.94', '116'],
    ['4费', '7.71', '7.94', '8.48', '6.17', '108'],
    ['5费', '9.23', '8.89', '10.15', '7.38', '70'],
    ['6费', '10.76', '10.28', '11.84', '8.61', '50'],
    ['7费', '12.29', '12.21', '13.52', '9.83', '42'],
    ['8费', '13.81', '14.38', '15.19', '11.05', '34'],
    ['9费', '15.34', '14.58', '16.87', '12.27', '26'],
    ['10费', '16.87', '18.60', '18.56', '13.50', '10'],
]
cost_table_data = [
    [Paragraph('<b>费用</b>', styles['TableHeader']),
     Paragraph('<b>期望属性</b>', styles['TableHeader']),
     Paragraph('<b>平均属性</b>', styles['TableHeader']),
     Paragraph('<b>高效阈值(>1.1)</b>', styles['TableHeader']),
     Paragraph('<b>亏模阈值(<0.8)</b>', styles['TableHeader']),
     Paragraph('<b>数量</b>', styles['TableHeader'])]
]
for row in cost_data_rows:
    cost_table_data.append([Paragraph(c, styles['TableCell']) for c in row])

cw = [60, 80, 80, 110, 110, 50]
t2 = Table(cost_table_data, colWidths=cw, hAlign='CENTER')
t2.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR),
    ('TEXTCOLOR', (0, 0), (-1, 0), TABLE_HEADER_TEXT),
    *[('BACKGROUND', (0, i), (-1, i), TABLE_ROW_EVEN if i % 2 == 1 else TABLE_ROW_ODD) for i in range(1, 11)],
    ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
]))
story.append(Spacer(1, 18))
story.append(t2)
story.append(Paragraph('表2：各费用段属性期望与效率阈值', styles['Caption']))
story.append(Spacer(1, 18))

# Chart 2
img2 = Image(chart_dir + 'chart2_mana_curve.png', width=440, height=189)
story.append(img2)
story.append(Paragraph('图2：标准模式随从费用分布与各费用稀有度分布', styles['Caption']))
story.append(Spacer(1, 18))

story.append(add_heading('<b>2.3 职业随从效率对比</b>', styles['H2'], 1))
story.append(Paragraph(
    '不同职业的随从属性效率存在显著差异。战士（平均效率1.115）和恶魔猎手（1.101）的随从在纯面板属性上最为突出，这与两个职业以场面交换为核心的战略定位高度一致。战士的大量增益效果（如怒袭、破甲等）需要随从存活才能发挥作用，因此其基础随从的面板质量普遍较高。恶魔猎手则依赖低费高效的随从快速铺场，配合英雄技能补刀来争夺场面控制权。',
    styles['Body']
))
story.append(Paragraph(
    '相比之下，圣骑士（0.907）和德鲁伊（0.915）的随从面板效率最低，但这恰恰反映了两个职业的设计哲学：圣骑士通过光环效果、祝福法术为随从提供额外增益，基础面板并非其核心优势；德鲁伊则通过选择机制（抉择）、跳费（激活、野性成长）和成长机制（如翡翠梦相关卡牌）来弥补面板的不足。因此，单纯比较面板效率并不能完全反映职业卡牌的实际强度，附加效果的量化评估需要更复杂的模型。',
    styles['Body']
))

img3 = Image(chart_dir + 'chart3_class_efficiency.png', width=420, height=245)
story.append(Spacer(1, 18))
story.append(img3)
story.append(Paragraph('图3：各职业随从平均属性效率对比（含标准差）', styles['Caption']))
story.append(Spacer(1, 18))

# ═══════════════════════════════════════
# SECTION 3: 对局抉择收益模型
# ═══════════════════════════════════════
story.append(add_heading('<b>三、对局抉择收益模型</b>', styles['H1'], 0))

story.append(Paragraph(
    '在对局中，玩家每回合都面临大量抉择：是出随从还是用法术？是打脸还是交换？是保留手牌还是全部打出？这些抉择的优劣取决于当前场面状态、双方剩余生命值、牌库深度等多维因素。本节构建了一套简化的数学模型，帮助玩家在有限的信息条件下快速评估各种抉择的预期收益。',
    styles['Body']
))

story.append(add_heading('<b>3.1 场面交换收益矩阵</b>', styles['H2'], 1))
story.append(Paragraph(
    '场面交换是炉石传说中最基础也最频繁的抉择之一。我们基于费用-属性模型，构建了一个8x8的交换收益矩阵。矩阵的行代表进攻方费用，列代表防守方费用，矩阵值代表交换的净收益。计算逻辑如下：假设进攻方的攻击力约为其总属性的65%，防守方的生命值约为其总属性的55%。如果进攻方的攻击力大于等于防守方的生命值，则进攻方能够击杀防守方并存活，收益为防守方的费用价值加上进攻方剩余生命值的贴现值（系数0.3）。如果不能一击击杀，则收益按伤害比例折算，并扣除进攻方被反击的损失（系数0.5）。',
    styles['Body']
))

story.append(Paragraph('<b>收益 = 击杀价值 + 存活贴现 - 进攻方被反击损失</b>', styles['Formula']))

img5 = Image(chart_dir + 'chart5_trade_matrix.png', width=420, height=280)
story.append(Spacer(1, 18))
story.append(img5)
story.append(Paragraph('图4：场面交换收益矩阵（绿色=有利，红色=不利）', styles['Caption']))
story.append(Spacer(1, 18))

story.append(Paragraph(
    '从矩阵中可以提取出几条关键对局原则：第一，低费打高费（如2费打5费）几乎总是有利的，即使进攻方不能一击击杀防守方，其费用投入也远低于防守方的损失。第二，高费打低费（如7费打2费）的收益通常很低甚至为负，因为高费随从的攻击力在打低血量目标时浪费了大量输出，且高费随从被低费随从换掉是巨大的节奏损失。第三，同费用交换的收益通常在2-5之间，取决于具体随从的攻防分配比例，因此"用3费随从换对面3费随从"通常是中性的，是否执行取决于场面需求的优先级。',
    styles['Body']
))

story.append(add_heading('<b>3.2 节奏价值模型</b>', styles['H2'], 1))
story.append(Paragraph(
    '节奏价值（Tempo Value）衡量的是每花费1点法力值能获得多少总属性。这一指标对于评估"跳费"策略（如德鲁伊的激活+高费随从）和"补费"策略（如萨满的过载）尤为关键。从图5可以看出，各费用段的实际平均属性/费比值波动较大，但总体趋势是：低费段（1-3费）的每费属性效率较高，高费段（8-10费）也有所回升，而中高费段（5-7费）则是效率的相对低谷。',
    styles['Body']
))
story.append(Paragraph(
    '这一发现具有重要的构筑意义：快攻卡组偏好1-3费随从，不仅因为这些随从可以早期铺场，更因为它们的每费属性效率本身就更高。控制卡组虽然使用大量高费卡牌，但7-10费段的效率回升（部分原因是传说卡牌的高质量面板和特殊机制）确保了后期回合的资源密度。中速卡组则处于一个微妙的中间位置，需要通过曲线优化和协同效应来弥补5-7费段的效率不足。',
    styles['Body']
))

img7 = Image(chart_dir + 'chart7_tempo_model.png', width=420, height=245)
story.append(Spacer(1, 18))
story.append(img7)
story.append(Paragraph('图5：各费用段每费属性效率对比', styles['Caption']))
story.append(Spacer(1, 18))

story.append(add_heading('<b>3.3 快速抉择计算框架</b>', styles['H2'], 1))
story.append(Paragraph(
    '基于上述模型，我们总结了一套适用于实际对局的快速抉择计算框架。该框架的核心思想是"费用价值守恒"：在评估任何操作时，将结果转化为等价的费用价值，然后比较操作的成本与收益。具体步骤如下：第一步，评估当前场面价值（将场上所有随从的期望属性转化为费用等价值）；第二步，模拟操作后的预期场面价值（考虑各种可能结果及其概率）；第三步，计算预期收益 = 操作后场面价值 - 操作前场面价值 - 操作成本（如消耗的法力值、失去的手牌等）。如果预期收益为正，则该操作值得执行。',
    styles['Body']
))

story.append(Paragraph(
    '举例说明：假设你有一个3费4/5随从（效率约1.07）在场，对面有一个2费3/2随从（效率约0.86）。用你的随从攻击对面的随从，预期结果是击杀对面（获得2费价值），你的随从剩余5-2=3血。此时你的操作成本为3费随从可能承受的风险，而收益为消灭一个2费随从。从交换矩阵来看，3费打2费的收益约为2-3点，属于中性偏正的交换。但如果你有更好的选择（如用英雄技能补刀或使用法术清除），则保留3费随从可能更优。最终决策还需考虑双方的套牌类型和对局阶段。',
    styles['Body']
))

img8 = Image(chart_dir + 'chart8_decision_reference.png', width=440, height=251)
story.append(Spacer(1, 18))
story.append(img8)
story.append(Paragraph('图6：快速抉择参考速查表', styles['Caption']))
story.append(Spacer(1, 18))

# ═══════════════════════════════════════
# SECTION 4: 流派收益分析
# ═══════════════════════════════════════
story.append(add_heading('<b>四、不同对局流派收益分析</b>', styles['H1'], 0))

story.append(Paragraph(
    '炉石传说中的卡组大致可分为四大流派：快攻（Aggro）、中速（Midrange）、控制（Control）和组合（Combo）。每个流派有不同的胜利条件、对局节奏和卡牌选择偏好，因此对卡牌属性效率的敏感度也各不相同。本节将基于标准模式卡牌数据，分析各流派在属性效率、费用曲线和收益特征上的差异。',
    styles['Body']
))

story.append(add_heading('<b>4.1 快攻流派</b>', styles['H2'], 1))
story.append(Paragraph(
    '快攻流派的核心理念是以最低的时间成本将对手的生命值降至零。其费用曲线集中在1-3费（建议占比约90%），4费及以上卡牌通常不超过3-4张。快攻对卡牌效率的要求极高，因为每张低费随从都必须在当回合最大化场面影响力。从标准模式数据来看，1费随从中效率排名前列的卡牌（如沉睡的林精，3/3面板效率1.92）是快攻卡组的优先选择。快攻的收益模型可以简化为：回合伤害期望 = 场上随从攻击力之和 + 法术伤害 + 英雄技能伤害。当对手生命值低于回合伤害期望时，快攻应全力打脸而非交换。',
    styles['Body']
))

story.append(add_heading('<b>4.2 中速流派</b>', styles['H2'], 1))
story.append(Paragraph(
    '中速流派的策略是在快攻和控制之间寻找平衡，通过稳定的场面发展和灵活的应对来赢得对局。费用曲线分布在2-5费（建议占比约80%），两端各有少量补充。中速卡组的独特优势在于"适应性"：它可以像快攻一样抢血，也可以像控制一样打资源消耗战。中速流派的收益判断最为复杂，需要同时考虑场面控制、手牌资源和对手套牌类型三个维度。一般来说，中速的核心法力值区间是3-4费，这两个费用的随从质量决定了中速卡组的强度下限。',
    styles['Body']
))

story.append(add_heading('<b>4.3 控制流派</b>', styles['H2'], 1))
story.append(Paragraph(
    '控制流派通过去除、恢复和资源积累来拖慢对局节奏，最终利用高价值卡牌在后期碾压对手。费用曲线偏重4费以上（建议占比60%以上），1-3费主要是去除法术和过牌工具。控制卡组对随从属性效率的要求相对宽松，因为它更关注卡牌的功能性（如AOE清除、回血、抽牌等）。从标准模式数据来看，控制卡组的高费随从（7-10费）平均效率较高，这反映了暴雪设计团队对高费卡牌面板质量的补偿性提升。例如，不败冠军（8费13/13，效率1.882）就是一张典型的控制体系终结者随从。',
    styles['Body']
))

story.append(add_heading('<b>4.4 组合流派</b>', styles['H2'], 1))
story.append(Paragraph(
    '组合流派依赖特定卡牌之间的协同效应，通过一回合内打出多个Combo来达成不可逆的优势或直接获胜。组合卡组的费用曲线取决于具体Combo的法力值需求，可能从0费到10费都有分布。组合卡组的核心收益公式为：Combo完成回合数 = 核心组件收集回合数期望 + 组件法力值总需求 / 平均每回合可用法力值。生存能力（回血、嘲讽、清除）和过牌效率（每回合稳定抽牌数量）是决定Combo完成速度的关键参数。组合卡组在属性效率上的要求最低，因为其胜利条件与随从面板质量几乎无关，关键在于Combo组件的可靠性和稳定性。',
    styles['Body']
))

img6 = Image(chart_dir + 'chart6_archetype_analysis.png', width=440, height=377)
story.append(Spacer(1, 18))
story.append(img6)
story.append(Paragraph('图7：不同流派卡牌效率分布对比', styles['Caption']))
story.append(Spacer(1, 18))

# ═══════════════════════════════════════
# SECTION 5: 法术伤害模型
# ═══════════════════════════════════════
story.append(add_heading('<b>五、法术卡牌伤害模型</b>', styles['H1'], 0))

story.append(Paragraph(
    '除随从面板属性外，法术的伤害效率也是对局抉择中的重要参考。我们通过自然语言处理技术，从标准模式328张法术卡牌的中文描述文本中提取了106条伤害数据，建立了法术费用-伤害的散点分析。需要说明的是，由于部分法术的伤害值受条件触发（如连击、流放、手牌条件等）影响，实际伤害可能高于或低于文本标注的基础值。因此本模型主要作为单卡价值评估的参考基准，而非精确计算工具。',
    styles['Body']
))

story.append(Paragraph(
    '从散点图分布来看，法术伤害与费用之间虽然存在正相关趋势，但离散程度远高于随从属性模型。这反映了法术设计的多样性：同费用法术可能在伤害、附加效果（吸血、冻结、抽牌等）、目标范围（单体/群体）之间做出不同取舍。例如，火球术（4费6点伤害）的纯伤害效率高达1.5点/费，是单目标去除的标杆；而暴风雪（6费2点伤害+冻结全体）则将大量费用价值分配给了控制效果而非直接伤害。',
    styles['Body']
))

img4 = Image(chart_dir + 'chart4_spell_damage.png', width=420, height=245)
story.append(Spacer(1, 18))
story.append(img4)
story.append(Paragraph('图8：标准模式法术费用-伤害关系散点图', styles['Caption']))
story.append(Spacer(1, 18))

# ═══════════════════════════════════════
# SECTION 6: 综合建议
# ═══════════════════════════════════════
story.append(add_heading('<b>六、综合决策建议</b>', styles['H1'], 0))

story.append(add_heading('<b>6.1 构筑阶段的量化参考</b>', styles['H2'], 1))
story.append(Paragraph(
    '在构筑卡组时，建议玩家利用本报告的效率指标进行初步筛选。对于快攻卡组，优先选择效率大于1.2的低费随从，确保前3回合的场面压力最大化。对于中速卡组，重点关注3-4费段的效率高于1.0的随从，它们是场面争夺的核心力量。对于控制卡组，不必过于追求面板效率，而应侧重于去除法术的覆盖范围和续航能力。无论哪个流派，都建议保留一定的过牌组件（每套卡组4-6张过牌卡），以降低关键卡牌的"死亡抽到"风险。费用曲线的平滑度也是重要指标，建议每个费用段至少有2-3张卡牌，避免出现"空费回合"。',
    styles['Body']
))

story.append(add_heading('<b>6.2 对局中的实时决策</b>', styles['H2'], 1))
story.append(Paragraph(
    '在实际对局中，建议玩家建立以下思维框架：每个回合开始时，首先评估双方场面价值的差距（利用交换矩阵快速估算），然后根据差距大小和对局阶段决定优先策略。前期（1-4回合）以争夺场面控制权为主，中期（5-7回合）根据双方剩余资源决定是加大攻势还是转入防守，后期（8回合+）则根据各自套牌类型执行终结计划。关键原则包括：不要用高费随从去换低费随从（除非是为了保护英雄生命值），在可以打脸击杀的回合不要贪图场面交换，以及在资源劣势时优先过牌而非铺场。',
    styles['Body']
))

story.append(add_heading('<b>6.3 模型局限性与进阶方向</b>', styles['H2'], 1))
story.append(Paragraph(
    '本报告的模型存在若干局限性，需要在使用时加以注意。首先，费用-属性线性模型仅解释了约70.8%的属性变异，其余近30%的变异来自随从的附加效果（战吼、亡语、光环、关键字等），这些效果的价值难以用统一标准量化。其次，交换收益矩阵假设了"期望属性"的平均攻防分配比例（65%攻击/35%生命），但实际卡牌的攻防比例差异极大（如1/30vs12/1），使用具体面板数据替代期望值可以获得更精确的结果。第三，本模型未考虑手牌优势、牌库深度、 fatigue 等长期资源维度，这些因素在控制对控制的对局中至关重要。未来可以将这些维度纳入模型，构建更全面的对局收益评估体系。',
    styles['Body']
))

# ━━ Build ━━
doc.multiBuild(story)
print(f"Body PDF generated: {output_path}")
