# -*- coding: utf-8 -*-
import os, sys
PDF_SKILL_DIR = "/home/z/my-project/skills/pdf"
_scripts = os.path.join(PDF_SKILL_DIR, "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)
from pdf import install_font_fallback

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import inch
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

pdfmetrics.registerFont(TTFont('Microsoft YaHei', '/usr/share/fonts/truetype/chinese/msyh.ttf'))
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))
registerFontFamily('Microsoft YaHei', normal='Microsoft YaHei', bold='Microsoft YaHei')
registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')
install_font_fallback()

ACCENT       = colors.HexColor('#d82442')
TEXT_PRIMARY  = colors.HexColor('#242220')
TEXT_MUTED    = colors.HexColor('#79746d')
BG_SURFACE   = colors.HexColor('#e3e0da')
TABLE_HEADER_COLOR = ACCENT
TABLE_HEADER_TEXT  = colors.white
TABLE_ROW_EVEN     = colors.white
TABLE_ROW_ODD      = BG_SURFACE

styles = {
    'Title': ParagraphStyle(name='Title', fontName='Microsoft YaHei', fontSize=24, leading=32, alignment=TA_CENTER, textColor=TEXT_PRIMARY, spaceAfter=12, wordWrap='CJK'),
    'H1': ParagraphStyle(name='H1', fontName='Microsoft YaHei', fontSize=18, leading=26, textColor=TEXT_PRIMARY, spaceBefore=18, spaceAfter=10, wordWrap='CJK'),
    'H2': ParagraphStyle(name='H2', fontName='Microsoft YaHei', fontSize=14, leading=20, textColor=ACCENT, spaceBefore=14, spaceAfter=8, wordWrap='CJK'),
    'Body': ParagraphStyle(name='Body', fontName='SimHei', fontSize=10.5, leading=18, alignment=TA_LEFT, textColor=TEXT_PRIMARY, firstLineIndent=21, wordWrap='CJK', spaceBefore=0, spaceAfter=4),
    'Formula': ParagraphStyle(name='Formula', fontName='SimHei', fontSize=11, leading=20, alignment=TA_CENTER, textColor=ACCENT, spaceBefore=8, spaceAfter=8, backColor=colors.HexColor('#fdf2f4'), borderPadding=8, wordWrap='CJK'),
    'Caption': ParagraphStyle(name='Caption', fontName='SimHei', fontSize=9, leading=14, alignment=TA_CENTER, textColor=TEXT_MUTED, spaceBefore=3, spaceAfter=6, wordWrap='CJK'),
    'TH': ParagraphStyle(name='TH', fontName='SimHei', fontSize=10, textColor=colors.white, alignment=TA_CENTER, wordWrap='CJK'),
    'TC': ParagraphStyle(name='TC', fontName='SimHei', fontSize=9.5, textColor=TEXT_PRIMARY, alignment=TA_CENTER, wordWrap='CJK'),
    'TCL': ParagraphStyle(name='TCL', fontName='SimHei', fontSize=9.5, textColor=TEXT_PRIMARY, alignment=TA_LEFT, wordWrap='CJK'),
}

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

ah = A4[1] - 2*inch
def skt(elements):
    total_h = sum(el.wrap(A4[0]-2*inch, A4[1])[1] for el in elements)
    if total_h <= ah * 0.4:
        return [KeepTogether(elements)]
    elif len(elements) >= 2:
        return [KeepTogether(elements[:2])] + list(elements[2:])
    return list(elements)

output_path = '/home/z/my-project/download/body_v2.pdf'
doc = TocDocTemplate(output_path, pagesize=A4, leftMargin=1*inch, rightMargin=1*inch, topMargin=0.8*inch, bottomMargin=0.8*inch)

story = []

# TOC
story.append(Paragraph('<b>目录</b>', styles['Title']))
story.append(Spacer(1, 12))
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle(name='TOC1', fontName='SimHei', fontSize=12, leftIndent=20, spaceBefore=4, spaceAfter=2, wordWrap='CJK'),
    ParagraphStyle(name='TOC2', fontName='SimHei', fontSize=10.5, leftIndent=40, spaceBefore=2, spaceAfter=1, wordWrap='CJK'),
]
story.append(toc)
story.append(PageBreak())

d = '/home/z/my-project/download/'

# ===== SECTION 1 =====
story.append(add_heading('<b>一、标准模式数据概览</b>', styles['H1'], 0))
story.append(Paragraph('本报告基于炉石传说"圣甲虫之年"（Year of the Scarab, 2026年3月起）标准模式卡牌数据，涵盖大灾变、穿越时空、失落之城、翡翠梦境四个扩展包，以及核心系列和活动卡组。数据来源为HearthstoneJSON API最新版本（中文），已包含35.0.3平衡补丁（2026年4月2日）的全部变更，共计984张可收集卡牌。报告围绕随从费用-属性数学模型、对局抉择收益模型、流派收益分析三大核心维度展开，并新增35.0.3补丁影响分析，旨在为玩家提供一套可量化的辅助决策工具。', styles['Body']))

story.append(add_heading('<b>1.1 卡牌类型分布</b>', styles['H2'], 1))
story.append(Paragraph('标准模式984张可收集卡牌中，随从（MINION）占据最大比例，共614张，占比约62.4%。法术（SPELL）紧随其后，共328张，占比33.3%。武器（WEAPON）仅有26张，地标（LOCATION）14张，英雄卡2张。随从和法术构成了标准模式的绝对主体，因此本报告的数学建模将重点围绕这两类卡牌展开。', styles['Body']))

td = [
    [Paragraph('<b>卡牌类型</b>', styles['TH']), Paragraph('<b>数量</b>', styles['TH']), Paragraph('<b>占比</b>', styles['TH'])],
    [Paragraph('随从', styles['TCL']), Paragraph('614', styles['TC']), Paragraph('62.4%', styles['TC'])],
    [Paragraph('法术', styles['TCL']), Paragraph('328', styles['TC']), Paragraph('33.3%', styles['TC'])],
    [Paragraph('武器', styles['TCL']), Paragraph('26', styles['TC']), Paragraph('2.6%', styles['TC'])],
    [Paragraph('地标', styles['TCL']), Paragraph('14', styles['TC']), Paragraph('1.4%', styles['TC'])],
    [Paragraph('英雄', styles['TCL']), Paragraph('2', styles['TC']), Paragraph('0.2%', styles['TC'])],
]
t = Table(td, colWidths=[150, 100, 100], hAlign='CENTER')
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_COLOR),
    ('TEXTCOLOR', (0,0), (-1,0), TABLE_HEADER_TEXT),
    *[('BACKGROUND', (0,i), (-1,i), TABLE_ROW_EVEN if i%2==1 else TABLE_ROW_ODD) for i in range(1,6)],
    ('GRID', (0,0), (-1,-1), 0.5, TEXT_MUTED),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8),
]))
story.append(Spacer(1, 18))
story.append(t)
story.append(Paragraph('表1：标准模式卡牌类型分布', styles['Caption']))
story.append(Spacer(1, 18))

story.append(add_heading('<b>1.2 35.0.3平衡补丁变更</b>', styles['H2'], 1))
story.append(Paragraph('2026年4月2日，暴雪发布了35.0.3平衡补丁，针对标准模式进行了7张卡牌的调整。此次补丁主要针对德鲁伊和萨满两个优势职业进行削弱，同时对部分潜力卡牌进行了加强。所有变更已反映在本报告的分析数据中。以下是完整的补丁变更清单：', styles['Body']))

patch_data = [
    [Paragraph('<b>卡牌名称</b>', styles['TH']), Paragraph('<b>职业</b>', styles['TH']), Paragraph('<b>类型</b>', styles['TH']), Paragraph('<b>变更内容</b>', styles['TH']), Paragraph('<b>方向</b>', styles['TH'])],
    [Paragraph('天空之墙哨兵', styles['TCL']), Paragraph('萨满', styles['TC']), Paragraph('随从', styles['TC']), Paragraph('0/3 变为 0/2', styles['TCL']), Paragraph('削弱', styles['TC'])],
    [Paragraph('火鹰飞翔', styles['TCL']), Paragraph('萨满', styles['TC']), Paragraph('法术', styles['TC']), Paragraph('+2/+2 变为 +1/+1', styles['TCL']), Paragraph('削弱', styles['TC'])],
    [Paragraph('角斗开战', styles['TCL']), Paragraph('萨满', styles['TC']), Paragraph('法术', styles['TC']), Paragraph('5费 变为 6费', styles['TCL']), Paragraph('削弱', styles['TC'])],
    [Paragraph('月亮井', styles['TCL']), Paragraph('德鲁伊', styles['TC']), Paragraph('法术', styles['TC']), Paragraph('7费 变为 6费', styles['TCL']), Paragraph('加强', styles['TC'])],
    [Paragraph('黑血', styles['TCL']), Paragraph('萨满', styles['TC']), Paragraph('随从', styles['TC']), Paragraph('4/8 变为 5/9', styles['TCL']), Paragraph('加强', styles['TC'])],
    [Paragraph('疯狂的追随者', styles['TCL']), Paragraph('潜行者', styles['TC']), Paragraph('随从', styles['TC']), Paragraph('3/1 变为 4/1', styles['TCL']), Paragraph('加强', styles['TC'])],
    [Paragraph('痴迷的技术员', styles['TCL']), Paragraph('死亡骑士', styles['TC']), Paragraph('随从', styles['TC']), Paragraph('2/5 变为 3/5', styles['TCL']), Paragraph('加强', styles['TC'])],
]
pt = Table(patch_data, colWidths=[100, 60, 50, 140, 50], hAlign='CENTER')
pt.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_COLOR),
    ('TEXTCOLOR', (0,0), (-1,0), TABLE_HEADER_TEXT),
    *[('BACKGROUND', (0,i), (-1,i), TABLE_ROW_EVEN if i%2==1 else TABLE_ROW_ODD) for i in range(1,8)],
    ('GRID', (0,0), (-1,-1), 0.5, TEXT_MUTED),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6),
]))
story.append(Spacer(1, 18))
story.append(pt)
story.append(Paragraph('表2：35.0.3补丁完整变更清单', styles['Caption']))
story.append(Spacer(1, 18))

story.append(Paragraph('从补丁影响来看，萨满职业受到最大冲击：天空之墙哨兵的生命值削减和火鹰飞翔的增益缩减直接影响了萨满的中期场面控制能力，角斗开战的费用提升则减缓了其跳费节奏。黑血的加强是暴雪对萨满后期终结能力的补偿性调整。德鲁伊方面，月亮井的减费使其AOE+回血手段更加灵活，但天空之墙哨兵的削弱对德鲁伊的跳费体系也有一定影响（该卡为中立卡，各职业通用）。', styles['Body']))

story.append(Paragraph('从效率模型角度分析，黑血从4/8（效率约0.91）提升至5/9（效率约1.01），从亏模卡一跃成为标准效率随从，其价值显著提升。天空之墙哨兵从0/3（效率约0.43）降至0/2（效率约0.29），进一步远离可用阈值，基本退出竞争性构筑。', styles['Body']))

img_patch = Image(d + 'chart_patch_impact.png', width=440, height=220)
story.append(Spacer(1, 18))
story.append(img_patch)
story.append(Paragraph('图1：35.0.3补丁影响卡牌效率分析', styles['Caption']))
story.append(Spacer(1, 18))

# ===== SECTION 2 =====
story.append(add_heading('<b>二、随从费用-属性数学模型</b>', styles['H1'], 0))
story.append(add_heading('<b>2.1 线性回归模型</b>', styles['H2'], 1))
story.append(Paragraph('通过对613张有效随从卡牌的法力值费用与总属性（攻击力+生命值）进行线性回归分析，得到如下高显著性模型。判定系数R平方值达到0.708，表明约70.8%的属性变异可以被费用差异所解释。这一比例相比全卡牌池（含狂野模式）有所降低，原因在于标准模式中存在更多带有特殊效果的"亏模"随从，它们以牺牲面板属性来换取战吼、亡语等附加价值。', styles['Body']))

story.append(Paragraph('<b>期望总属性 = 1.53 x 费用 + 1.60</b>', styles['Formula']))
story.append(Paragraph('R平方 = 0.708, P值 < 0.001', styles['Caption']))

story.append(Paragraph('该模型的含义十分直观：每增加1点法力值费用，随从的期望总属性增加约1.53点。截距1.60代表0费随从的基础属性期望值。基于此模型，我们定义"属性效率"指标：效率 = 实际总属性 / 期望总属性。效率大于1.0意味着面板超模，小于1.0则意味着亏模。许多亏模随从的附加效果足以弥补面板不足，因此效率指标应与其他因素综合考虑。', styles['Body']))

img1 = Image(d + 'chart1_cost_stats_model.png', width=440, height=256)
story.append(Spacer(1, 18))
story.append(img1)
story.append(Paragraph('图2：标准模式随从费用-属性散点图与线性回归模型', styles['Caption']))
story.append(Spacer(1, 18))

story.append(add_heading('<b>2.2 各费用段属性统计与效率阈值</b>', styles['H2'], 1))
story.append(Paragraph('下表展示了每个费用段的平均属性值和效率关键阈值。1费和2费随从的效率波动最大，这反映了低费随从在快攻与控制体系中的价值差异。高费用段（7-10费）虽然卡牌数量较少，但平均效率有所回升，这与传说卡牌的高质量面板和补偿性设计密切相关。', styles['Body']))

cost_rows = [['1费','3.13','3.02','3.44','2.50','55'],['2费','4.65','4.72','5.12','3.72','101'],['3费','6.18','6.24','6.80','4.94','116'],['4费','7.71','7.94','8.48','6.17','108'],['5费','9.23','8.89','10.15','7.38','70'],['6费','10.76','10.28','11.84','8.61','50'],['7费','12.29','12.21','13.52','9.83','42'],['8费','13.81','14.38','15.19','11.05','34'],['9费','15.34','14.58','16.87','12.27','26'],['10费','16.87','18.60','18.56','13.50','10']]
ct = [[Paragraph('<b>费用</b>', styles['TH']), Paragraph('<b>期望属性</b>', styles['TH']), Paragraph('<b>平均属性</b>', styles['TH']), Paragraph('<b>高效阈值(>1.1)</b>', styles['TH']), Paragraph('<b>亏模阈值(<0.8)</b>', styles['TH']), Paragraph('<b>数量</b>', styles['TH'])]]
for r in cost_rows:
    ct.append([Paragraph(c, styles['TC']) for c in r])
t2 = Table(ct, colWidths=[60,80,80,110,110,50], hAlign='CENTER')
t2.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_COLOR), ('TEXTCOLOR', (0,0), (-1,0), TABLE_HEADER_TEXT),
    *[('BACKGROUND', (0,i), (-1,i), TABLE_ROW_EVEN if i%2==1 else TABLE_ROW_ODD) for i in range(1,11)],
    ('GRID', (0,0), (-1,-1), 0.5, TEXT_MUTED), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6),
]))
story.append(Spacer(1, 18))
story.append(t2)
story.append(Paragraph('表3：各费用段属性期望与效率阈值', styles['Caption']))
story.append(Spacer(1, 18))

story.append(add_heading('<b>2.3 效率Top 20随从排名</b>', styles['H2'], 1))
story.append(Paragraph('以下图表展示了标准模式中面板效率最高的20张随从。需要注意的是，高效率并不等同于高实战价值——许多超模随从都有严格的触发条件或负面效果（如布洛克斯加需要手牌中有特定卡牌才能获得12/12面板）。但效率排名可以帮助玩家快速识别那些"白送属性"的优质卡牌，作为构筑的起点参考。', styles['Body']))

img_top = Image(d + 'chart_top20_efficiency.png', width=420, height=280)
story.append(Spacer(1, 18))
story.append(img_top)
story.append(Paragraph('图3：标准模式随从效率Top 20', styles['Caption']))
story.append(Spacer(1, 18))

story.append(add_heading('<b>2.4 职业随从效率对比</b>', styles['H2'], 1))
story.append(Paragraph('不同职业的随从属性效率存在显著差异。战士（平均效率1.115）和恶魔猎手（1.101）的随从在纯面板属性上最为突出，这与两个职业以场面交换为核心的战略定位高度一致。相比之下，圣骑士（0.907）和德鲁伊（0.915）的随从面板效率最低，反映了这两个职业通过增益效果和机制弥补面板不足的设计哲学。', styles['Body']))

img3 = Image(d + 'chart3_class_efficiency.png', width=420, height=245)
story.append(Spacer(1, 18))
story.append(img3)
story.append(Paragraph('图4：各职业随从平均属性效率对比', styles['Caption']))
story.append(Spacer(1, 18))

img2 = Image(d + 'chart_mana_curve_updated.png', width=420, height=245)
story.append(img2)
story.append(Paragraph('图5：标准模式随从费用分布', styles['Caption']))
story.append(Spacer(1, 18))

# ===== SECTION 3 =====
story.append(add_heading('<b>三、对局抉择收益模型</b>', styles['H1'], 0))
story.append(Paragraph('在对局中，玩家每回合都面临大量抉择：是出随从还是用法术？是打脸还是交换？本节构建了一套简化的数学模型，帮助玩家在有限信息条件下快速评估各种抉择的预期收益。', styles['Body']))

story.append(add_heading('<b>3.1 场面交换收益矩阵</b>', styles['H2'], 1))
story.append(Paragraph('我们基于费用-属性模型构建了一个8x8的交换收益矩阵。行代表进攻方费用，列代表防守方费用，矩阵值代表交换的净收益。计算逻辑：假设进攻方攻击力约为总属性的65%，防守方生命值约为总属性的55%。若进攻方能一击击杀防守方，收益为防守方费用价值加上进攻方剩余生命值的贴现值（系数0.3）；否则按伤害比例折算并扣除反击损失。', styles['Body']))
story.append(Paragraph('<b>收益 = 击杀价值 + 存活贴现 - 进攻方被反击损失</b>', styles['Formula']))

img5 = Image(d + 'chart5_trade_matrix.png', width=420, height=280)
story.append(Spacer(1, 18))
story.append(img5)
story.append(Paragraph('图6：场面交换收益矩阵', styles['Caption']))
story.append(Spacer(1, 18))

story.append(Paragraph('从矩阵中可以提取出几条关键原则：第一，低费打高费（如2费打5费）几乎总是有利的。第二，高费打低费（如7费打2费）收益通常很低甚至为负，高费随从被低费换掉是巨大的节奏损失。第三，同费用交换收益通常在2-5之间，属于中性偏正。', styles['Body']))

story.append(add_heading('<b>3.2 节奏价值模型</b>', styles['H2'], 1))
story.append(Paragraph('节奏价值衡量每花费1点法力值能获得多少总属性。低费段（1-3费）的每费属性效率较高，高费段（8-10费）也有所回升，而中高费段（5-7费）则是效率相对低谷。快攻卡组偏好1-3费不仅因为早期铺场，更因为每费效率本身就更高。控制卡组后期效率回升确保了资源密度。中速卡组则需要通过曲线优化弥补5-7费段的效率不足。', styles['Body']))

img7 = Image(d + 'chart7_tempo_model.png', width=420, height=245)
story.append(Spacer(1, 18))
story.append(img7)
story.append(Paragraph('图7：各费用段每费属性效率对比', styles['Caption']))
story.append(Spacer(1, 18))

story.append(add_heading('<b>3.3 快速抉择计算框架</b>', styles['H2'], 1))
story.append(Paragraph('基于上述模型，我们总结了一套适用于实际对局的快速抉择计算框架。核心思想是"费用价值守恒"：评估任何操作时，将结果转化为等价的费用价值，然后比较操作的成本与收益。具体步骤：第一步，评估当前场面价值；第二步，模拟操作后的预期场面价值；第三步，计算预期收益 = 操作后场面价值 - 操作前场面价值 - 操作成本。', styles['Body']))

img8 = Image(d + 'chart8_decision_reference.png', width=440, height=251)
story.append(Spacer(1, 18))
story.append(img8)
story.append(Paragraph('图8：快速抉择参考速查表', styles['Caption']))
story.append(Spacer(1, 18))

# ===== SECTION 4 =====
story.append(add_heading('<b>四、不同对局流派收益分析</b>', styles['H1'], 0))
story.append(Paragraph('炉石传说中的卡组大致可分为四大流派：快攻（Aggro）、中速（Midrange）、控制（Control）和组合（Combo）。每个流派有不同的胜利条件和对局节奏，对卡牌属性效率的敏感度也各不相同。', styles['Body']))

story.append(add_heading('<b>4.1 快攻流派</b>', styles['H2'], 1))
story.append(Paragraph('快攻流派的核心理念是以最低的时间成本将对手生命值降至零。费用曲线集中在1-3费（建议占比约90%），4费及以上卡牌通常不超过3-4张。快攻对卡牌效率的要求极高，因为每张低费随从都必须在当回合最大化场面影响力。快攻的收益模型：回合伤害期望 = 场上随从攻击力之和 + 法术伤害 + 英雄技能伤害。当对手生命值低于回合伤害期望时，应全力打脸而非交换。', styles['Body']))

story.append(add_heading('<b>4.2 中速流派</b>', styles['H2'], 1))
story.append(Paragraph('中速流派在快攻和控制之间寻找平衡，通过稳定的场面发展和灵活应对来赢得对局。费用曲线分布在2-5费（建议占比约80%）。中速的核心法力值区间是3-4费，这两个费用的随从质量决定了中速卡组的强度下限。中速的收益判断最为复杂，需同时考虑场面控制、手牌资源和对手套牌类型三个维度。', styles['Body']))

story.append(add_heading('<b>4.3 控制流派</b>', styles['H2'], 1))
story.append(Paragraph('控制流派通过去除、恢复和资源积累来拖慢对局节奏，最终利用高价值卡牌在后期碾压对手。费用曲线偏重4费以上（建议占比60%以上）。控制对随从属性效率要求相对宽松，更关注卡牌功能性（AOE清除、回血、抽牌）。高费随从平均效率较高（如不败冠军8费13/13，效率1.882），反映了暴雪对高费卡牌的补偿性设计。', styles['Body']))

story.append(add_heading('<b>4.4 组合流派</b>', styles['H2'], 1))
story.append(Paragraph('组合流派依赖特定卡牌之间的协同效应，通过Combo达成不可逆的优势或直接获胜。组合卡组的费用曲线取决于具体Combo需求，可能从0费到10费都有分布。核心收益公式：Combo完成回合数 = 核心组件收集回合数期望 + 组件法力值总需求 / 平均每回合可用法力值。生存能力和过牌效率是决定Combo完成速度的关键参数。', styles['Body']))

img6 = Image(d + 'chart6_archetype_analysis.png', width=440, height=377)
story.append(Spacer(1, 18))
story.append(img6)
story.append(Paragraph('图9：不同流派卡牌效率分布对比', styles['Caption']))
story.append(Spacer(1, 18))

# ===== SECTION 5 =====
story.append(add_heading('<b>五、法术卡牌伤害模型</b>', styles['H1'], 0))
story.append(Paragraph('通过自然语言处理技术从328张法术卡牌的中文描述中提取了106条伤害数据，建立法术费用-伤害散点分析。法术伤害与费用之间的离散程度远高于随从属性模型，反映了法术设计的多样性：同费用法术可能在伤害、附加效果（吸血、冻结、抽牌等）、目标范围之间做出不同取舍。', styles['Body']))

img4 = Image(d + 'chart4_spell_damage.png', width=420, height=245)
story.append(Spacer(1, 18))
story.append(img4)
story.append(Paragraph('图10：标准模式法术费用-伤害关系散点图', styles['Caption']))
story.append(Spacer(1, 18))

# ===== SECTION 6 =====
story.append(add_heading('<b>六、综合决策建议</b>', styles['H1'], 0))
story.append(add_heading('<b>6.1 构筑阶段的量化参考</b>', styles['H2'], 1))
story.append(Paragraph('在构筑卡组时，建议利用效率指标进行初步筛选。快攻卡组优先选择效率大于1.2的低费随从。中速卡组重点关注3-4费段效率高于1.0的随从。控制卡组不必过于追求面板效率，侧重于去除法术覆盖范围和续航能力。无论哪个流派，建议保留4-6张过牌卡以降低关键卡牌的"死亡抽到"风险。费用曲线平滑度也很重要，每个费用段至少2-3张卡牌。', styles['Body']))

story.append(add_heading('<b>6.2 对局中的实时决策</b>', styles['H2'], 1))
story.append(Paragraph('每个回合开始时，首先评估双方场面价值差距（利用交换矩阵快速估算），然后根据差距和对局阶段决定优先策略。前期（1-4回合）以争夺场面控制权为主，中期（5-7回合）根据剩余资源决定攻势或防守，后期（8回合+）执行终结计划。关键原则：不要用高费随从换低费随从；可以打脸击杀时不要贪图场面交换；资源劣势时优先过牌而非铺场。', styles['Body']))

story.append(add_heading('<b>6.3 补丁后的环境变化与应对</b>', styles['H2'], 1))
story.append(Paragraph('35.0.3补丁后，德鲁伊和萨满的强度有所回落，环境可能出现多元化趋势。对构筑的具体影响包括：萨满卡组需要重新评估天空之墙哨兵的替代品，火鹰飞翔的增益缩减可能影响中速萨满的曲线流畅度；德鲁伊的月亮井减费使其更加灵活，但整体削弱方向可能促使德鲁伊从跳费快攻转向传统中速或控制路线。黑血的加强为萨满控制体系提供了新的后期选择，值得密切关注。', styles['Body']))

story.append(add_heading('<b>6.4 模型局限性</b>', styles['H2'], 1))
story.append(Paragraph('本模型存在若干局限性：费用-属性线性模型仅解释约70.8%的属性变异，其余来自附加效果（战吼、亡语、光环等），难以用统一标准量化。交换矩阵假设平均攻防比例（65%攻击/35%生命），实际差异大。模型未考虑手牌优势、牌库深度、fatigue等长期资源维度。未来可将这些维度纳入，构建更全面的对局收益评估体系。', styles['Body']))

doc.multiBuild(story)
print(f"Body v2 generated: {output_path}")
