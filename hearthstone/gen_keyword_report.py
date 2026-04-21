# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, '/home/z/my-project/skills/pdf/scripts')
from pdf import install_font_fallback

import json
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                 Table, TableStyle, Image, KeepTogether, CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# ========== Font Registration ==========
pdfmetrics.registerFont(TTFont('Microsoft YaHei', '/usr/share/fonts/truetype/chinese/msyh.ttf'))
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
registerFontFamily('Microsoft YaHei', normal='Microsoft YaHei', bold='Microsoft YaHei')
registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')
install_font_fallback()

# ========== Palette ==========
ACCENT = colors.HexColor('#ce364f')
TEXT_PRIMARY = colors.HexColor('#242220')
TEXT_MUTED = colors.HexColor('#807b73')
BG_SURFACE = colors.HexColor('#dfdcd7')
BG_PAGE = colors.HexColor('#f3f1ef')
TABLE_HEADER_COLOR = ACCENT
TABLE_HEADER_TEXT = colors.white
TABLE_ROW_EVEN = colors.white
TABLE_ROW_ODD = BG_SURFACE

# ========== Load Data ==========
with open('/home/z/my-project/hearthstone/keyword_deep_analysis.json', 'r') as f:
    analysis = json.load(f)

# ========== Styles ==========
PAGE_W, PAGE_H = A4
LEFT_M = 1.0 * inch
RIGHT_M = 1.0 * inch
TOP_M = 0.8 * inch
BOT_M = 0.8 * inch
AVAIL_W = PAGE_W - LEFT_M - RIGHT_M

styles = getSampleStyleSheet()

h1_style = ParagraphStyle(
    name='H1', fontName='Microsoft YaHei', fontSize=20, leading=28,
    textColor=TEXT_PRIMARY, spaceBefore=18, spaceAfter=12, alignment=TA_LEFT,
    wordWrap='CJK'
)
h2_style = ParagraphStyle(
    name='H2', fontName='Microsoft YaHei', fontSize=15, leading=22,
    textColor=ACCENT, spaceBefore=14, spaceAfter=8, alignment=TA_LEFT,
    wordWrap='CJK'
)
h3_style = ParagraphStyle(
    name='H3', fontName='Microsoft YaHei', fontSize=12, leading=18,
    textColor=TEXT_PRIMARY, spaceBefore=10, spaceAfter=6, alignment=TA_LEFT,
    wordWrap='CJK'
)
body_style = ParagraphStyle(
    name='Body', fontName='SimHei', fontSize=10.5, leading=18,
    textColor=TEXT_PRIMARY, spaceBefore=0, spaceAfter=6,
    alignment=TA_LEFT, wordWrap='CJK', firstLineIndent=21
)
body_no_indent = ParagraphStyle(
    name='BodyNoIndent', fontName='SimHei', fontSize=10.5, leading=18,
    textColor=TEXT_PRIMARY, spaceBefore=0, spaceAfter=6,
    alignment=TA_LEFT, wordWrap='CJK'
)
caption_style = ParagraphStyle(
    name='Caption', fontName='SimHei', fontSize=9, leading=14,
    textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=3, spaceAfter=6,
    wordWrap='CJK'
)
header_cell = ParagraphStyle(
    name='HeaderCell', fontName='SimHei', fontSize=10, leading=14,
    textColor=colors.white, alignment=TA_CENTER, wordWrap='CJK'
)
data_cell = ParagraphStyle(
    name='DataCell', fontName='SimHei', fontSize=9.5, leading=14,
    textColor=TEXT_PRIMARY, alignment=TA_CENTER, wordWrap='CJK'
)
data_cell_left = ParagraphStyle(
    name='DataCellLeft', fontName='SimHei', fontSize=9.5, leading=14,
    textColor=TEXT_PRIMARY, alignment=TA_LEFT, wordWrap='CJK'
)

# ========== TOC Template ==========
class TocDocTemplate(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if hasattr(flowable, 'bookmark_name'):
            level = getattr(flowable, 'bookmark_level', 0)
            text = getattr(flowable, 'bookmark_text', '')
            key = getattr(flowable, 'bookmark_key', '')
            self.notify('TOCEntry', (level, text, self.page, key))

def add_heading(text, style, level=0):
    key = 'h_%s' % hashlib.md5(text.encode()).hexdigest()[:8]
    p = Paragraph('<a name="%s"/><b>%s</b>' % (key, text), style)
    p.bookmark_name = text
    p.bookmark_level = level
    p.bookmark_text = text
    p.bookmark_key = key
    return p

def make_table(data_rows, col_widths, has_header=True):
    table = Table(data_rows, colWidths=col_widths, hAlign='CENTER')
    style_cmds = [
        ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    if has_header:
        style_cmds.append(('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR))
        style_cmds.append(('TEXTCOLOR', (0, 0), (-1, 0), TABLE_HEADER_TEXT))
        for i in range(1, len(data_rows)):
            bg = TABLE_ROW_EVEN if i % 2 == 1 else TABLE_ROW_ODD
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
    table.setStyle(TableStyle(style_cmds))
    return table

def add_img(path, max_w=AVAIL_W, max_h=300):
    from reportlab.lib.utils import ImageReader
    img = Image(path)
    w, h = img.drawWidth, img.drawHeight
    ratio = min(max_w / w, max_h / h, 1.0)
    img.drawWidth = w * ratio
    img.drawHeight = h * ratio
    return img

# ========== Build Document ==========
output_path = '/home/z/my-project/download/hs_keyword_body.pdf'
doc = TocDocTemplate(
    output_path, pagesize=A4,
    leftMargin=LEFT_M, rightMargin=RIGHT_M,
    topMargin=TOP_M, bottomMargin=BOT_M
)

story = []

# --- TOC ---
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle(name='TOC1', fontSize=12, leftIndent=20, fontName='SimHei', leading=22, spaceBefore=6),
    ParagraphStyle(name='TOC2', fontSize=10, leftIndent=40, fontName='SimHei', leading=18, spaceBefore=3),
]
story.append(Paragraph('<b>目  录</b>', ParagraphStyle(
    name='TOCTitle', fontName='Microsoft YaHei', fontSize=22, leading=30,
    textColor=TEXT_PRIMARY, alignment=TA_CENTER, spaceBefore=20, spaceAfter=20
)))
story.append(toc)
story.append(PageBreak())

# ========== Chapter 1: Overview ==========
story.append(add_heading('一、数据概览与分析背景', h1_style, 0))
story.append(Spacer(1, 6))

story.append(Paragraph(
    '本报告基于HearthstoneJSON API获取的最新卡牌数据，聚焦于2026年圣甲虫之年标准模式环境下的关键词机制分析。'
    '当前标准模式共包含973张可收集卡牌，来自5个卡组：核心(Core 2026)、大灾变(CATACLYSM)、翡翠之梦(EMERALD_DREAM)、'
    '失落之城(THE_LOST_CITY)和时光之旅(TIME_TRAVEL)。其中随从607张、法术325张、武器25张、地标14张、英雄2张。',
    body_style
))
story.append(Paragraph(
    '关键词(Keyword/Mechanic)是炉石传说卡牌系统的核心机制之一，它定义了卡牌的触发条件、战吼效果、'
    '亡语结算、属性增益等功能行为。不同关键词在卡池中的分布密度和效率差异，直接影响各流派的构筑策略和对局博弈。'
    '本报告从关键词数量分布、属性效率、费用结构、职业特征和多关键词组合五个维度进行综合量化分析，'
    '旨在为玩家提供一套基于数据的关键词认知框架，辅助套牌构筑和对局决策。',
    body_style
))

story.append(add_heading('1.1 卡组构成与类型分布', h2_style, 1))

set_data = [
    [Paragraph('<b>卡组</b>', header_cell), Paragraph('<b>卡牌数</b>', header_cell), Paragraph('<b>占比</b>', header_cell)],
    [Paragraph('核心(Core 2026)', data_cell), Paragraph('289', data_cell), Paragraph('29.7%', data_cell)],
    [Paragraph('大灾变(CATACLYSM)', data_cell), Paragraph('135', data_cell), Paragraph('13.9%', data_cell)],
    [Paragraph('翡翠之梦(EMERALD_DREAM)', data_cell), Paragraph('183', data_cell), Paragraph('18.8%', data_cell)],
    [Paragraph('失落之城(THE_LOST_CITY)', data_cell), Paragraph('183', data_cell), Paragraph('18.8%', data_cell)],
    [Paragraph('时光之旅(TIME_TRAVEL)', data_cell), Paragraph('183', data_cell), Paragraph('18.8%', data_cell)],
]
cw = [AVAIL_W * 0.45, AVAIL_W * 0.28, AVAIL_W * 0.27]
story.append(Spacer(1, 12))
story.append(make_table(set_data, cw))
story.append(Paragraph('表1 标准模式卡组构成（总计973张可收集卡牌）', caption_style))
story.append(Spacer(1, 12))

type_data = [
    [Paragraph('<b>卡牌类型</b>', header_cell), Paragraph('<b>数量</b>', header_cell), Paragraph('<b>占比</b>', header_cell)],
    [Paragraph('随从(MINION)', data_cell), Paragraph('607', data_cell), Paragraph('62.4%', data_cell)],
    [Paragraph('法术(SPELL)', data_cell), Paragraph('325', data_cell), Paragraph('33.4%', data_cell)],
    [Paragraph('武器(WEAPON)', data_cell), Paragraph('25', data_cell), Paragraph('2.6%', data_cell)],
    [Paragraph('地标(LOCATION)', data_cell), Paragraph('14', data_cell), Paragraph('1.4%', data_cell)],
    [Paragraph('英雄(HERO)', data_cell), Paragraph('2', data_cell), Paragraph('0.2%', data_cell)],
]
story.append(Spacer(1, 12))
story.append(make_table(type_data, cw))
story.append(Paragraph('表2 卡牌类型分布', caption_style))

# ========== Chapter 2: Keyword Distribution ==========
story.append(Spacer(1, 18))
story.append(add_heading('二、关键词数量分布分析', h1_style, 0))
story.append(Spacer(1, 6))

story.append(Paragraph(
    '在973张标准模式卡牌中，具有至少一个核心关键词的卡牌共522张（覆盖率53.7%），其中随从占据绝大多数。'
    '战吼以307张的绝对数量优势位居榜首，几乎覆盖了一半的随从卡牌。亡语以108张排名第二，是第二大高频关键词。'
    '嘲讽(78张)、发现(68张)和突袭(36张)构成了第二梯队。这五大关键词合计占总关键词卡牌的97%以上，'
    '构成了标准模式的关键词生态核心。',
    body_style
))
story.append(Paragraph(
    '值得注意的是，任务(12张)和奥秘(10张)虽然数量不多，但对特定职业（猎人、法师、圣骑士）的构筑方向有着决定性的影响。'
    '掘底、注能、腐蚀等较新机制的卡牌数量较少，但这些机制的卡牌往往具有独特的战略价值，'
    '能够在特定套牌中发挥不可替代的作用。发现机制以68张的数量跨越了随从、法术和地标三种卡牌类型，'
    '体现了暴雪设计团队对"灵活获取"机制的持续投入。',
    body_style
))

story.append(add_heading('2.1 关键词数量排名', h2_style, 1))
story.append(Spacer(1, 8))
story.append(add_img('/home/z/my-project/download/chart1_keyword_count_top15.png', max_h=260))
story.append(Paragraph('图1 标准模式关键词卡牌数量排名TOP15', caption_style))

story.append(add_heading('2.2 关键词按卡牌类型分布', h2_style, 1))
story.append(Paragraph(
    '关键词在不同卡牌类型中的分布差异显著。战吼主要集中在随从(298张)和武器(8张)，'
    '这反映了战吼作为"打出即触发"的设计理念——随从和武器是最常见的主动打出型卡牌。'
    '发现机制在法术(38张)和随从(28张)中均有较高分布，法术卡通过发现可以灵活补充手牌资源，'
    '而随从的发现效果则更偏向于场面增益。突袭和嘲讽几乎完全限定在随从中，'
    '作为战斗阶段的核心攻防属性。吸血关键词分布在随从(18张)、法术(7张)和武器(2张)三类卡牌中，'
    '其中法术吸血（如暗影之箭、灵魂虹吸）为控制型套牌提供了额外的续航能力。',
    body_style
))

story.append(Spacer(1, 12))
story.append(add_img('/home/z/my-project/download/chart6_keyword_type_coverage.png', max_h=230))
story.append(Paragraph('图2 高频关键词按卡牌类型分布及各职业关键词覆盖率', caption_style))

# ========== Chapter 3: Efficiency Analysis ==========
story.append(Spacer(1, 18))
story.append(add_heading('三、关键词属性效率分析', h1_style, 0))
story.append(Spacer(1, 6))

baseline = analysis['baseline']
story.append(Paragraph(
    '本章基于费用-属性线性回归模型对关键词卡牌的面板效率进行量化评估。基线模型为：'
    '每个法力值消耗提供约1.96点总属性（攻击力+生命值），即期望属性 = 1.96 x 费用。'
    '全体607张随从的平均效率差值为%.3f，即平均而言随从的实际属性略高于模型预测值。'
    '效率差值定义为：(实际总属性 - 期望属性) / 费用，正值表示该卡牌/关键词组合超模，负值表示亏模。'
    % baseline['efficiency'],
    body_style
))

story.append(add_heading('3.1 关键词效率差值总览', h2_style, 1))
story.append(Paragraph(
    '效率分析揭示了关键词的"隐性成本"差异。冲锋关键词虽然仅有4张卡牌，但效率差高达+2.437，'
    '这意味着冲锋卡的面板属性远超同费用期望——这恰恰体现了冲锋机制本身的高风险性（对手回合可直接攻击英雄），'
    '设计师通过高面板来补偿机制缺陷。过载(+1.731)和法术伤害(+0.321)也呈现超模特征，'
    '分别因过载的下回合费用惩罚和法术伤害的被动增益性质而获得面板补偿。',
    body_style
))
story.append(Paragraph(
    '另一方面，圣盾(-0.478)、重生(-0.533)和剧毒(-0.580)的效率差均为较大负值，'
    '说明这些关键词的"机制价值"很高，需要通过削减面板属性来平衡。圣盾的完全格挡一次伤害、'
    '重生的亡语再召唤、剧毒的击杀保证，这些机制在对局中的实际价值远超其面板亏损。'
    '亡语(-0.176)和突袭(-0.175)的效率亏损相对温和，属于中等机制成本的代表性关键词。'
    '战吼(-0.033)的效率差接近于零，这看似矛盾——实际上战吼效果的多样性极大，'
    '从简单的buff到复杂的价值引擎应有尽有，因此其平均面板接近基线是多种效果相互抵消的结果。',
    body_style
))

story.append(Spacer(1, 8))
story.append(add_img('/home/z/my-project/download/chart2_keyword_efficiency.png', max_h=260))
story.append(Paragraph('图3 关键词属性效率对比（基于E=1.96C模型）', caption_style))

story.append(add_heading('3.2 关键词效率详细数据', h2_style, 1))

kw_eff = analysis['keyword_efficiency']
eff_rows = [[
    Paragraph('<b>关键词</b>', header_cell),
    Paragraph('<b>效率差</b>', header_cell),
    Paragraph('<b>数量</b>', header_cell),
    Paragraph('<b>均费</b>', header_cell),
    Paragraph('<b>均属性</b>', header_cell),
]]
sorted_eff = sorted(kw_eff.items(), key=lambda x: x[1]['eff_vs_baseline'], reverse=True)
for name, d in sorted_eff:
    sign = '+' if d['eff_vs_baseline'] >= 0 else ''
    eff_rows.append([
        Paragraph(name, data_cell_left),
        Paragraph('%s%.3f' % (sign, d['eff_vs_baseline']), data_cell),
        Paragraph(str(d['count']), data_cell),
        Paragraph('%.2f' % d['avg_cost'], data_cell),
        Paragraph('%.1f' % d['avg_stats'], data_cell),
    ])
cw2 = [AVAIL_W*0.22, AVAIL_W*0.22, AVAIL_W*0.15, AVAIL_W*0.20, AVAIL_W*0.21]
story.append(Spacer(1, 12))
story.append(make_table(eff_rows, cw2))
story.append(Paragraph('表3 关键词属性效率详细对比', caption_style))

# ========== Chapter 4: Cost Structure ==========
story.append(Spacer(1, 18))
story.append(add_heading('四、关键词费用结构分析', h1_style, 0))
story.append(Spacer(1, 6))

story.append(Paragraph(
    '不同关键词卡牌的费用分布反映了设计意图和实战定位。突袭关键词的平均费用最高(5.89)，'
    '中位数达到6费，这说明突袭随从主要定位于中后期解决场面问题——通过高费用配合即时攻击能力，'
    '在打出当回合即可参与交换，适合控制和中速套牌。嘲讽的平均费用为5.24，同样偏高，'
    '体现了嘲讽作为防御机制在中后期回合的价值——高费用嘲讽墙能有效拖延快攻节奏。',
    body_style
))
story.append(Paragraph(
    '发现机制的平均费用仅为3.18，中位数3费，是典型的前中期机制。这符合发现的实战定位：'
    '在游戏早期通过灵活择取卡牌来规划中后期策略。战吼(均值4.06)和亡语(均值4.32)的费用分布'
    '覆盖了0费到10费的全范围，箱线图显示战吼在中低费用段(2-5费)有密集分布，'
    '而亡语的分布更为均匀。吸血(均值5.11)的费用分布偏高，反映了吸血作为续航机制'
    '在中后期回合更具战略价值的设计取向。',
    body_style
))

story.append(Spacer(1, 8))
story.append(add_img('/home/z/my-project/download/chart3_keyword_cost_boxplot.png', max_h=260))
story.append(Paragraph('图4 核心关键词费用分布箱线图', caption_style))

# Cost distribution table
cost_rows = [[
    Paragraph('<b>关键词</b>', header_cell),
    Paragraph('<b>费用范围</b>', header_cell),
    Paragraph('<b>均值</b>', header_cell),
    Paragraph('<b>中位数</b>', header_cell),
    Paragraph('<b>定位</b>', header_cell),
]]
cost_info = [
    ('战吼', '0~10', '4.06', '4.0', '全费用段'),
    ('亡语', '1~10', '4.32', '4.0', '全费用段'),
    ('嘲讽', '0~10', '5.24', '5.0', '中后期防御'),
    ('发现', '1~8', '3.18', '3.0', '前中期能量'),
    ('突袭', '2~10', '5.89', '6.0', '中后期解场'),
    ('吸血', '1~9', '5.11', '4.5', '中后期续航'),
]
for kw, rng, avg, med, role in cost_info:
    cost_rows.append([
        Paragraph(kw, data_cell_left),
        Paragraph(rng, data_cell),
        Paragraph(avg, data_cell),
        Paragraph(med, data_cell),
        Paragraph(role, data_cell),
    ])
cw3 = [AVAIL_W*0.18, AVAIL_W*0.22, AVAIL_W*0.18, AVAIL_W*0.20, AVAIL_W*0.22]
story.append(Spacer(1, 12))
story.append(make_table(cost_rows, cw3))
story.append(Paragraph('表4 核心关键词费用结构对比', caption_style))

# ========== Chapter 5: Class Analysis ==========
story.append(Spacer(1, 18))
story.append(add_heading('五、各职业关键词特征分析', h1_style, 0))
story.append(Spacer(1, 6))

story.append(Paragraph(
    '各职业的关键词分布呈现出鲜明的职业特色。术士以22张战吼卡排名第一，'
    '加上10张亡语和5张发现，构成了"主动触发+被动收益"的双引擎体系，'
    '这与其牺牲生命值换取卡牌优势的种族特色高度契合。牧师以20张战吼和8张吸血为核心，'
    '体现了"控制+回复"的蓝白职业定位。战士(21张战吼)和潜行者(19张战吼)紧随其后，'
    '但潜行者的9张连击卡独树一帜，形成了独特的连击链构筑空间。',
    body_style
))
story.append(Paragraph(
    '职业特色关键词方面：德鲁伊拥有9张抉择卡(全场最多)，延续了"灵活选择"的设计传统；'
    '萨满以10张过载卡独占鳌头，配合7张嘲讽形成了"过载节奏+嘲讽防御"的典型构筑思路；'
    '圣骑士以7张圣盾卡领跑，圣盾+战吼的组合(24张卡中的常见搭配)使其在中速对局中具有出色的交换效率。'
    '猎人(5张奥秘)和法师(5张奥秘+5张发现)则分别代表了奥秘控场和发现择取两种资源管理策略。',
    body_style
))

story.append(Spacer(1, 8))
story.append(add_img('/home/z/my-project/download/chart4_class_keyword_heatmap.png', max_h=280))
story.append(Paragraph('图5 各职业关键词分布热力图', caption_style))

story.append(add_heading('5.1 职业关键词覆盖率', h2_style, 1))
story.append(Paragraph(
    '关键词覆盖率反映了各职业卡牌的"机制密度"。中立卡(250张)中有181张(72.4%)带有核心关键词，'
    '远高于职业卡(约53%)，说明中立卡更多承担"功能卡"角色——通过关键词机制而非职业特色来提供价值。'
    '在职业卡中，萨满(60.9%)覆盖率最高，恶魔猎手(59.4%)、潜行者(59.4%)和术士(59.4%)紧随其后，'
    '这些职业的卡牌设计中机制含量更高。法师(48.4%)和圣骑士(47.0%)的覆盖率相对较低，'
    '这可能反映了这些职业更多依赖基础面板和法术直伤而非关键词互动的设计取向。',
    body_style
))

# Class coverage table
cov_rows = [[
    Paragraph('<b>职业</b>', header_cell),
    Paragraph('<b>关键词卡牌</b>', header_cell),
    Paragraph('<b>总卡牌</b>', header_cell),
    Paragraph('<b>覆盖率</b>', header_cell),
    Paragraph('<b>核心特征</b>', header_cell),
]]
class_info = [
    ('萨满', '39', '64', '60.9%', '过载+嘲讽'),
    ('恶魔猎手', '38', '64', '59.4%', '突袭+发现'),
    ('潜行者', '38', '64', '59.4%', '连击+潜行'),
    ('术士', '38', '64', '59.4%', '战吼+亡语'),
    ('猎人', '33', '64', '51.6%', '战吼+奥秘'),
    ('牧师', '33', '64', '51.6%', '战吼+吸血'),
    ('战士', '33', '64', '51.6%', '战吼+嘲讽'),
    ('德鲁伊', '32', '64', '50.0%', '抉择+发现'),
    ('法师', '31', '64', '48.4%', '发现+奥秘'),
    ('圣骑士', '31', '66', '47.0%', '圣盾+战吼'),
    ('中立', '181', '250', '72.4%', '战吼+亡语'),
]
for cls, kw_c, total, rate, feat in class_info:
    cov_rows.append([
        Paragraph(cls, data_cell_left),
        Paragraph(kw_c, data_cell),
        Paragraph(total, data_cell),
        Paragraph(rate, data_cell),
        Paragraph(feat, data_cell),
    ])
cw4 = [AVAIL_W*0.16, AVAIL_W*0.20, AVAIL_W*0.18, AVAIL_W*0.18, AVAIL_W*0.28]
story.append(Spacer(1, 12))
story.append(make_table(cov_rows, cw4))
story.append(Paragraph('表5 各职业关键词覆盖率及核心特征', caption_style))

# ========== Chapter 6: Multi-keyword Combos ==========
story.append(Spacer(1, 18))
story.append(add_heading('六、多关键词组合分析', h1_style, 0))
story.append(Spacer(1, 6))

story.append(Paragraph(
    '在973张标准模式卡牌中，拥有两个及以上核心关键词的卡牌共155张(15.9%)。'
    '多关键词组合是衡量卡牌复杂度和战略深度的重要指标。发现+战吼(25张)是最常见的双关键词组合，'
    '这种组合允许玩家在打出时从卡库中择取一张卡牌，兼具灵活性和场面影响力。'
    '嘲讽+战吼(24张)排名第二，典型卡如"始生研习"等既能在打出时产生效果又能充当防御墙。',
    body_style
))
story.append(Paragraph(
    '亡语+嘲讽(19张)是第三大组合，形成了"死亡后仍然有防御价值"的双重保障机制。'
    '亡语+战吼(16张)则提供了"打出触发+死亡再触发"的双周期价值引擎，'
    '这类卡牌在中速和控制套牌中具有极高的综合收益。圣盾+嘲讽(3张)虽然数量不多，'
    '但"双保"效果(圣盾挡一次伤害+嘲讽强制攻击)使其成为快攻克星。'
    '三关键词组合（如亡语+嘲讽+圣盾）仅有2张，属于极为稀有但机制丰富的"万金油"卡牌。',
    body_style
))

story.append(Spacer(1, 8))
story.append(add_img('/home/z/my-project/download/chart5_keyword_combos.png', max_h=220))
story.append(Paragraph('图6 多关键词组合排名TOP10', caption_style))

# Combo detail table
combos = analysis['multi_keyword_combos']
combo_rows = [[
    Paragraph('<b>关键词组合</b>', header_cell),
    Paragraph('<b>卡牌数</b>', header_cell),
    Paragraph('<b>组合特征</b>', header_cell),
]]
combo_desc = {
    '发现+战吼': '灵活择取+即时效果',
    '嘲讽+战吼': '防御墙+主动触发',
    '亡语+嘲讽': '死亡防御+双周期',
    '亡语+战吼': '双触发价值引擎',
    '吸血+战吼': '回复+主动触发',
    '可交易+战吼': '手牌调节+主动触发',
    '战吼+突袭': '即时效果+即时攻击',
    '亡语+突袭': '死亡效果+解场能力',
}
sorted_combos = sorted(combos.items(), key=lambda x: x[1], reverse=True)[:10]
for combo, cnt in sorted_combos:
    desc = combo_desc.get(combo, '复合机制')
    combo_rows.append([
        Paragraph(combo, data_cell_left),
        Paragraph(str(cnt), data_cell),
        Paragraph(desc, data_cell),
    ])
cw5 = [AVAIL_W*0.35, AVAIL_W*0.20, AVAIL_W*0.45]
story.append(Spacer(1, 12))
story.append(make_table(combo_rows, cw5))
story.append(Paragraph('表6 多关键词组合特征', caption_style))

# ========== Chapter 7: Decision Model ==========
story.append(Spacer(1, 18))
story.append(add_heading('七、关键词策略决策模型', h1_style, 0))
story.append(Spacer(1, 6))

story.append(add_heading('7.1 关键词价值评估框架', h2_style, 1))
story.append(Paragraph(
    '综合以上分析，我们可以构建一个基于关键词的对局决策评估框架。该框架将关键词的实战价值分解为'
    '三个维度：面板效率(属性是否超模)、机制价值(关键词在对局中的实际影响力)和费用适配度'
    '(关键词卡的费用是否符合当前对局节奏)。',
    body_style
))

story.append(Paragraph(
    '面板效率维度：冲锋(+2.44)和过载(+1.73)具有显著的面板溢价，选择这些卡牌时可以期待高于平均的'
    '基础属性。而圣盾(-0.48)、重生(-0.53)和剧毒(-0.58)需要约0.5点/费的面板亏损来平衡其强大的机制效果，'
    '实际评估时应将机制收益纳入总价值计算。战吼(-0.03)接近平衡线，其价值完全取决于战吼效果的具体内容。',
    body_style
))

story.append(Paragraph(
    '机制价值维度：嘲讽在对局中具有"强制攻击"的战术价值，在快攻对局中1点嘲讽约等于2-3点有效生命值。'
    '突袭的"即时解场"能力相当于免费一次攻击行动。发现的"择取优势"约为1.5张卡的价值(三选一)。'
    '亡语的"不可被沉默前阻止"特性使其具有抗干扰优势，尤其在对抗控制套牌时价值更高。',
    body_style
))

story.append(Paragraph(
    '费用适配度维度：快攻套牌应优先选择3费以下的关键词卡(发现、战吼低费段)，'
    '中速套牌适合4-6费段(战吼、嘲讽中费段)，控制套牌可大量使用6费以上高价值关键词卡'
    '(突袭、吸血、嘲讽高费段)。过载关键词在中速萨满中有特殊的节奏价值，'
    '但需精确计算下回合的费用影响。',
    body_style
))

story.append(add_heading('7.2 流派关键词偏好矩阵', h2_style, 1))

arch_rows = [[
    Paragraph('<b>流派</b>', header_cell),
    Paragraph('<b>优先关键词</b>', header_cell),
    Paragraph('<b>费用偏好</b>', header_cell),
    Paragraph('<b>核心逻辑</b>', header_cell),
]]
arch_data = [
    ('快攻', '突袭、圣盾、风怒', '1~3费', '高效交换、快速抢血'),
    ('中速', '战吼、发现、嘲讽', '3~6费', '节奏控制、资源积累'),
    ('控制', '亡语、吸血、嘲讽', '5~8费', '价值引擎、场面交换'),
    ('组合', '战吼、发现、任务', '全费用段', '过牌搜索、条件达成'),
]
for arch, kw, cost, logic in arch_data:
    arch_rows.append([
        Paragraph(arch, data_cell),
        Paragraph(kw, data_cell_left),
        Paragraph(cost, data_cell),
        Paragraph(logic, data_cell_left),
    ])
cw6 = [AVAIL_W*0.14, AVAIL_W*0.28, AVAIL_W*0.18, AVAIL_W*0.40]
story.append(Spacer(1, 12))
story.append(make_table(arch_rows, cw6))
story.append(Paragraph('表7 流派关键词偏好矩阵', caption_style))

# ========== Build ==========
doc.multiBuild(story)
print(f"Body PDF generated: {output_path}")
