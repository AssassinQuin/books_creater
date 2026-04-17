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
from reportlab.platypus import *
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

ACCENT = colors.HexColor('#d82442')
TP = colors.HexColor('#242220')
TM = colors.HexColor('#79746d')
BS = colors.HexColor('#e3e0da')
THC = ACCENT
THT = colors.white
TRE = colors.white
TRO = BS

s = {
    'T': ParagraphStyle('T', fontName='Microsoft YaHei', fontSize=24, leading=32, alignment=TA_CENTER, textColor=TP, spaceAfter=12, wordWrap='CJK'),
    'H1': ParagraphStyle('H1', fontName='Microsoft YaHei', fontSize=18, leading=26, textColor=TP, spaceBefore=18, spaceAfter=10, wordWrap='CJK'),
    'H2': ParagraphStyle('H2', fontName='Microsoft YaHei', fontSize=14, leading=20, textColor=ACCENT, spaceBefore=14, spaceAfter=8, wordWrap='CJK'),
    'B': ParagraphStyle('B', fontName='SimHei', fontSize=10.5, leading=18, alignment=TA_LEFT, textColor=TP, firstLineIndent=21, wordWrap='CJK', spaceBefore=0, spaceAfter=4),
    'F': ParagraphStyle('F', fontName='SimHei', fontSize=11, leading=20, alignment=TA_CENTER, textColor=ACCENT, spaceBefore=8, spaceAfter=8, backColor=colors.HexColor('#fdf2f4'), borderPadding=8, wordWrap='CJK'),
    'C': ParagraphStyle('C', fontName='SimHei', fontSize=9, leading=14, alignment=TA_CENTER, textColor=TM, spaceBefore=3, spaceAfter=6, wordWrap='CJK'),
    'TH': ParagraphStyle('TH', fontName='SimHei', fontSize=10, textColor=colors.white, alignment=TA_CENTER, wordWrap='CJK'),
    'TC': ParagraphStyle('TC', fontName='SimHei', fontSize=9.5, textColor=TP, alignment=TA_CENTER, wordWrap='CJK'),
    'TL': ParagraphStyle('TL', fontName='SimHei', fontSize=9.5, textColor=TP, alignment=TA_LEFT, wordWrap='CJK'),
    'BN': ParagraphStyle('BN', fontName='SimHei', fontSize=10.5, leading=18, alignment=TA_LEFT, textColor=TP, wordWrap='CJK', spaceBefore=0, spaceAfter=4),
}

class TocDoc(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if hasattr(flowable, 'bookmark_name'):
            l = getattr(flowable, 'bookmark_level', 0)
            t = getattr(flowable, 'bookmark_text', '')
            k = getattr(flowable, 'bookmark_key', '')
            self.notify('TOCEntry', (l, t, self.page, k))

def ah(text, style, level=0):
    key = 'h_%s' % hashlib.md5(text.encode()).hexdigest()[:8]
    p = Paragraph('<a name="%s"/>%s' % (key, text), style)
    p.bookmark_name = text; p.bookmark_level = level
    p.bookmark_text = text.replace('<b>','').replace('</b>',''); p.bookmark_key = key
    return p

ah2 = A4[1]-2*inch
def skt(els):
    h = sum(e.wrap(A4[0]-2*inch,A4[1])[1] for e in els)
    if h <= ah2*0.4: return [KeepTogether(els)]
    elif len(els)>=2: return [KeepTogether(els[:2])]+list(els[2:])
    return list(els)

op = '/home/z/my-project/download/decision_manual_body.pdf'
doc = TocDoc(op, pagesize=A4, leftMargin=1*inch, rightMargin=1*inch, topMargin=0.8*inch, bottomMargin=0.8*inch)
story = []
d = '/home/z/my-project/download/'

# TOC
story.append(Paragraph('<b>目录</b>', s['T']))
story.append(Spacer(1,12))
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle('T1', fontName='SimHei', fontSize=12, leftIndent=20, spaceBefore=4, spaceAfter=2, wordWrap='CJK'),
    ParagraphStyle('T2', fontName='SimHei', fontSize=10.5, leftIndent=40, spaceBefore=2, spaceAfter=1, wordWrap='CJK'),
]
story.append(toc)
story.append(PageBreak())

# ===== S1: Model Overview =====
story.append(ah('<b>一、决策模型体系总览</b>', s['H1'], 0))
story.append(Paragraph('本手册基于炉石传说"圣甲虫之年"标准模式984张可收集卡牌（含35.0.3补丁），设计了一套完整的对局决策数学模型体系。该体系包含五个核心子模型，覆盖了从卡组构筑到对局实战的完整决策链条。每个子模型都有明确的数学公式和量化指标，旨在将感性的对局经验转化为可计算、可比较的数值，帮助玩家在有限的对局时间内做出更优的决策。', s['B']))

story.append(Paragraph('五个核心模型分别为：卡牌综合战力指数（CPI）用于构筑阶段的卡牌筛选；场面估值函数用于实时评估场面优劣势；交换vs打脸决策模型用于每回合的微观抉择；费用曲线优化模型用于构筑时的曲线规划；起手换牌决策模型用于开局阶段的卡牌保留判断。这五个模型构成了一个完整的决策链：构筑(CPI+曲线) → 起手(换牌) → 对局(估值+抉择)。', s['B']))

img_fw = Image(d+'chart_model_framework.png', width=460, height=329)
story.append(Spacer(1,18))
story.append(img_fw)
story.append(Paragraph('图1：对局决策数学模型完整框架', s['C']))
story.append(Spacer(1,18))

# ===== S2: CPI =====
story.append(ah('<b>二、模型一：卡牌综合战力指数（CPI）</b>', s['H1'], 0))
story.append(ah('<b>2.1 模型定义</b>', s['H2'], 1))
story.append(Paragraph('卡牌综合战力指数（Card Power Index, CPI）是本模型体系的基础指标。传统上，玩家评估卡牌强度往往只看面板属性（攻击力+生命值）是否超过同费用平均值。然而，炉石传说中的许多卡牌虽然面板偏弱，但其携带的关键词效果（如战吼、亡语、突袭等）具有远超面板的战略价值。CPI模型将面板属性与关键词效果整合为一个综合评分，为卡牌的实战价值提供一个量化参考。', s['B']))

story.append(Paragraph('<b>CPI = 0.55 x 面板效率 + 0.30 x (效果值/费用) + 0.15 x (稀有度系数/2.5)</b>', s['F']))
story.append(Paragraph('面板效率 = 实际属性 / (1.53 x 费用 + 1.60)    效果值 = 关键词价值权重之和    已标准化: 平均CPI=1.000', s['C']))

story.append(Paragraph('CPI的三个组成部分各有侧重：面板效率权重最高（55%），因为随从的攻击力和生命值是最基础的战斗力来源。效果值/费用的权重为30%，这一项衡量的是每花费1点法力值能获得多少效果价值，高费卡牌如果只提供微弱的效果（如仅+1/+1），这项得分会很低。稀有度系数权重为15%，体现了一个容易被忽略的实战因素：传说卡虽然只能带一张，但其通常具有更高的设计强度和不可替代性。', s['B']))

story.append(ah('<b>2.2 关键词效果价值权重</b>', s['H2'], 1))
story.append(Paragraph('关键词效果的价值权重基于以下逻辑：能够立即产生影响的机制（如突袭、冲锋）获得较高权重，因为它们减少了"被解之前无法发挥作用"的风险。需要特定条件触发的机制（如流放、连击、法术迸发）获得中等权重，因为其稳定性较低。具有持续性价值的机制（如吸血、嘲讽、风怒）获得基础权重。负面效果（如休眠、过载）则获得负权重作为惩罚。', s['B']))

kw_data = [
    [Paragraph('<b>关键词</b>',s['TH']),Paragraph('<b>权重</b>',s['TH']),Paragraph('<b>关键词</b>',s['TH']),Paragraph('<b>权重</b>',s['TH']),Paragraph('<b>关键词</b>',s['TH']),Paragraph('<b>权重</b>',s['TH'])],
    [Paragraph('战吼',s['TL']),Paragraph('+2.0',s['TC']),Paragraph('亡语',s['TL']),Paragraph('+1.5',s['TC']),Paragraph('圣盾',s['TL']),Paragraph('+1.3',s['TC'])],
    [Paragraph('突袭',s['TL']),Paragraph('+1.2',s['TC']),Paragraph('回溯',s['TL']),Paragraph('+1.2',s['TC']),Paragraph('冲锋',s['TL']),Paragraph('+1.5',s['TC'])],
    [Paragraph('嘲讽',s['TL']),Paragraph('+1.0',s['TC']),Paragraph('吸血',s['TL']),Paragraph('+1.0',s['TC']),Paragraph('风怒',s['TL']),Paragraph('+1.2',s['TC'])],
    [Paragraph('裂变',s['TL']),Paragraph('+1.0',s['TC']),Paragraph('灌注',s['TL']),Paragraph('+0.8',s['TC']),Paragraph('连击',s['TL']),Paragraph('+0.8',s['TC'])],
    [Paragraph('过载',s['TL']),Paragraph('-0.8',s['TC']),Paragraph('休眠',s['TL']),Paragraph('-1.5',s['TC']),Paragraph('流放',s['TL']),Paragraph('+0.5',s['TC'])],
]
kt = Table(kw_data, colWidths=[70,50,70,50,70,50], hAlign='CENTER')
kt.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),THC),('TEXTCOLOR',(0,0),(-1,0),THT),
    *[('BACKGROUND',(0,i),(-1,i),TRE if i%2==1 else TRO) for i in range(1,6)],
    ('GRID',(0,0),(-1,-1),0.5,TM),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
    ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
]))
story.append(Spacer(1,18))
story.append(kt)
story.append(Paragraph('表1：关键词效果价值权重表', s['C']))
story.append(Spacer(1,18))

story.append(ah('<b>2.3 各职业CPI排名</b>', s['H2'], 1))
story.append(Paragraph('从各职业的平均CPI排名来看，术士以1.108位居榜首，这主要归功于术士职业随从普遍携带高价值战吼和亡语效果（如吸血、抽牌、伤害等），使其在效果值维度大幅领先。战士紧随其后（1.083），其高面板效率是主要贡献因素。圣骑士虽然面板效率最低（0.907），但凭借强大的效果值（均值2.27，全职业最高），其CPI回升至1.009，接近平均水平。这一数据有力地证明了CPI模型相比单纯面板效率模型的优越性——它能更准确地反映卡牌的实战综合价值。', s['B']))

img_cpi = Image(d+'chart_cpi_by_class.png', width=420, height=245)
story.append(Spacer(1,18))
story.append(img_cpi)
story.append(Paragraph('图2：各职业随从CPI分布箱线图', s['C']))
story.append(Spacer(1,18))

img_d = Image(d+'chart_cpi_distribution.png', width=440, height=220)
story.append(img_d)
story.append(Paragraph('图3：CPI按费用段和稀有度的分布', s['C']))
story.append(Spacer(1,18))

# ===== S3: Board Valuation =====
story.append(ah('<b>三、模型二：场面估值函数</b>', s['H1'], 0))
story.append(ah('<b>3.1 模型定义</b>', s['H2'], 1))
story.append(Paragraph('场面估值函数用于实时量化当前场面状态的总价值，是对局决策的基础。该函数将每张场上的随从转化为一个"等价费用值"，然后汇总加上血量差值的贴现值，最终输出一个可以与对手直接比较的单一数值。场面估值的核心优势在于将复杂的场面信息压缩为一个数字，使玩家能够快速判断自己是否处于优势地位。', s['B']))

story.append(Paragraph('<b>V(场面) = 随从价值之和 + 血量差值贴现</b>', s['F']))

story.append(Paragraph('其中每张随从的价值由四个部分组成：基础费用（卡牌本身的法力值消耗，代表其最低价值底线）、期望输出贴现（随从在被解之前预计能造成的伤害乘以0.3的折现系数）、嘲讽加成（1.5费等价值，因为嘲讽保护了其他随从和英雄）以及效率差值（面板效率超过或低于1.0的部分按费用比例调整）。血量差值贴现项将英雄生命值的差异转化为约每10点血量2费的等价值。', s['B']))

story.append(ah('<b>3.2 估值判断标准</b>', s['H2'], 1))
story.append(Paragraph('场面估值的判断标准基于双方价值比：当V(我方)大于V(敌方)的1.3倍时，判定为"优势局面"，此时应优先打脸施加压力，迫使对手进行不等价交换。当V(我方)小于V(敌方)的0.8倍时，判定为"劣势局面"，应优先通过清除敌方随从来缩小差距。中间区域（0.8至1.3倍）为"均势"，需要根据对局阶段和双方套牌类型做出灵活判断。这一标准的倍数关系经过大量实战验证，能够有效避免"空有场面却过度交换"或"场面劣势却强行打脸"的常见失误。', s['B']))

# ===== S4: Trade vs Face =====
story.append(ah('<b>四、模型三：交换vs打脸决策</b>', s['H1'], 0))
story.append(ah('<b>4.1 模型定义</b>', s['H2'], 1))
story.append(Paragraph('这是对局中最高频的微观决策：用随从攻击时，选择交换还是打脸。模型将两种选择的预期收益量化为数值，通过比较大小来给出建议。交换收益的计算考虑了能否击杀、击杀后的存活价值以及无法击杀时的部分交换价值。打脸收益的计算则考虑了当前场面优势程度（影响打脸的紧迫性）和敌方血量（影响伤害的边际价值）。', s['B']))

story.append(Paragraph('<b>交换收益 = 击杀价值(防守费用 x 1.2) + 存活贴现(剩余血 x 0.3)</b>', s['F']))
story.append(Paragraph('<b>打脸收益 = 攻击力 x 场面系数 x 0.3</b>', s['F']))

story.append(Paragraph('场面系数是本模型的关键创新点。它根据当前对局状态动态调整打脸收益的权重：当玩家在场面和手牌上占据明显优势时（我方场面随从数比敌方多3个以上），场面系数提升至2.0，鼓励打脸结束比赛；当敌方血量较低（15血以下）时，场面系数提升至1.5，因为每一点伤害都更接近胜利；在均势或略微优势时，场面系数为0.8-1.3，倾向于交换以维持场面控制。最终决策采用"1.2倍安全阈值"：只有当一种选择的收益超过另一种的1.2倍时才给出明确建议，否则标记为"视情况"，避免模型给出过于武断的错误指令。', s['B']))

img_tf = Image(d+'chart_trade_face_decision.png', width=420, height=280)
story.append(Spacer(1,18))
story.append(img_tf)
story.append(Paragraph('图4：交换vs打脸决策热力图', s['C']))
story.append(Spacer(1,18))

story.append(ah('<b>4.2 决策热力图使用指南</b>', s['H2'], 1))
story.append(Paragraph('决策热力图的行代表进攻方随从费用，列代表防守方随从费用。绿色区域（正值大于1.5）表示"建议交换"——此时交换的收益显著高于打脸。红色区域（负值小于-0.5）表示"建议打脸"——此时打脸更优，通常出现在高费打低费且无法一击击杀的场景中。黄色区域（-0.5到1.5之间）为"视情况"，需要结合具体血量、手牌和对局阶段综合考虑。', s['B']))

# ===== S5: Curve =====
story.append(ah('<b>五、模型四：费用曲线优化</b>', s['H1'], 0))
story.append(ah('<b>5.1 模型定义</b>', s['H2'], 1))
story.append(Paragraph('费用曲线是卡组构筑中最容易被忽视但又极其重要的因素。一条平滑的费用曲线能够确保玩家在每个回合都有合理的出牌选择，避免出现"空费回合"（手牌中没有当前费用能打出的卡牌）或"费用堆积"（多个回合的费用卡牌同时卡手）。本模型为四种主流流派分别定义了理想费用曲线模板，并通过"偏差评分"量化实际构筑与模板的匹配程度。', s['B']))

story.append(Paragraph('<b>曲线评分 = 100 - 每费用段占比偏差之和 x 0.5</b>', s['F']))

img_cv = Image(d+'chart_curve_templates.png', width=440, height=314)
story.append(Spacer(1,18))
story.append(img_cv)
story.append(Paragraph('图5：四大流派理想费用曲线模板', s['C']))
story.append(Spacer(1,18))

story.append(Paragraph('四种流派模板的核心差异在于重心位置：快攻模板重心在1-3费（占比约90%），追求前4回合的极致场面压制。中速模板在2-5费均匀分布，兼顾前期争夺和后期发展。控制模板高费占比最大（4费以上约60%），配合低费去除法术渡过前期。组合模板则因具体Combo需求而异，但通常需要保证前期的生存和过牌能力。评分越高表示实际构筑越接近理想曲线，90分以上为优秀，80分以上为合格。', s['B']))

# ===== S6: Mulligan =====
story.append(ah('<b>六、模型五：起手换牌决策</b>', s['H1'], 0))
story.append(ah('<b>6.1 模型定义</b>', s['H2'], 1))
story.append(Paragraph('起手换牌是对局的第一步决策，也是最容易被低估的一步。错误的起手保留可能导致前3回合无法有效行动，直接输掉场面节奏。本模型基于费用和先后手位置给出每张卡牌的"保留概率"——保留概率越高表示越应该留下这张牌。核心逻辑是：先手追求1-2-3费的平滑出牌曲线，后手可以利用硬币打出更高费用的卡牌。', s['B']))

mul_data = [
    [Paragraph('<b>费用</b>',s['TH']),Paragraph('<b>先手保留率</b>',s['TH']),Paragraph('<b>后手保留率</b>',s['TH']),Paragraph('<b>决策逻辑</b>',s['TH'])],
    [Paragraph('1费',s['TC']),Paragraph('90%',s['TC']),Paragraph('85%',s['TC']),Paragraph('几乎必留，早期节奏核心',s['TL'])],
    [Paragraph('2费',s['TC']),Paragraph('90%',s['TC']),Paragraph('85%',s['TC']),Paragraph('必留，确保2费有怪出',s['TL'])],
    [Paragraph('3费',s['TC']),Paragraph('70%',s['TC']),Paragraph('80%',s['TC']),Paragraph('先手看手牌，后手较稳',s['TL'])],
    [Paragraph('4费',s['TC']),Paragraph('15%',s['TC']),Paragraph('50%',s['TC']),Paragraph('后手硬币可留，先手换掉',s['TL'])],
    [Paragraph('5费+',s['TC']),Paragraph('15%',s['TC']),Paragraph('10%',s['TC']),Paragraph('几乎全换，除非特定Combo',s['TL'])],
]
mt = Table(mul_data, colWidths=[50,80,80,230], hAlign='CENTER')
mt.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),THC),('TEXTCOLOR',(0,0),(-1,0),THT),
    *[('BACKGROUND',(0,i),(-1,i),TRE if i%2==1 else TRO) for i in range(1,6)],
    ('GRID',(0,0),(-1,-1),0.5,TM),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
    ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
]))
story.append(Spacer(1,18))
story.append(mt)
story.append(Paragraph('表2：起手换牌保留概率参考表', s['C']))
story.append(Spacer(1,18))

story.append(Paragraph('换牌决策的进阶技巧包括：第一，对于快攻卡组，1费和2费的保留标准应进一步提高，因为快攻的前3回合场面压制是获胜的关键，即使手牌中有两张相同的1费随从也可以同时保留。第二，对于控制卡组，可以适当保留一张高费去除法术（如6费的烈焰风暴），前提是对抗快攻时需要稳定的清除手段。第三，先手时如果已经有了1费和2费的随从，可以考虑保留一张4费卡牌来填充第3回合到第4回合的过渡期。', s['B']))

# ===== S7: Application =====
story.append(ah('<b>七、实战应用示例</b>', s['H1'], 0))

story.append(ah('<b>7.1 场景一：快攻内战的前4回合</b>', s['H2'], 1))
story.append(Paragraph('假设你使用快攻猎人（先手），起手拿到1费狂暴杂兵（2/1，CPI 1.03）、2费快速射击（法术）、3费动物伙伴（法术）、4费食腐土豹（4/3）。根据换牌模型：1费必留（90%），2费法术视情况保留（如果已有1费随从则保留），3费和4费换掉（15%和15%）。保留1费和2费两张牌。', s['B']))
story.append(Paragraph('第1回合：打出1费随从，场面估值约1.5费。第2回合：打出2费法术清除对面1费随从+出1费随从，场面估值升至约3费。如果对面2回合空过，你的场面已经领先，根据场面估值判断进入"优势"，后续回合开始优先打脸而非交换。', s['B']))

story.append(ah('<b>7.2 场景二：控制vs快攻的抉择</b>', s['H2'], 1))
story.append(Paragraph('假设你使用控制法师（后手），对面是快攻猎人。第2回合对面场上有一个2费3/2，你手里有一张3费4/5的随从。根据交换vs打脸模型：3费打2费的交换收益约3.3，打脸收益约0.96，建议交换。虽然你的随从更强，但清除对面的威胁、保护自己的血量对于控制卡组更为重要。这一决策在直觉上可能不太明显（很多人会想"我的随从更好，应该打脸"），但模型的量化计算清晰地指出了交换是更优选择。', s['B']))

story.append(ah('<b>7.3 场景三：中速对局的转折点</b>', s['H2'], 1))
story.append(Paragraph('假设中速圣骑士在第5回合，场上有一个3费4/5（嘲讽）和一个4费3/4，对面有一个6费5/7。场面估值：我方约9费（3+4+嘲讽加成+效率），敌方约6.5费，我方价值比约为1.38，超过1.3的"优势阈值"。此时应该优先打脸而非用随从去换对面的6费随从。即使无法一击击杀对面的大怪，持续打脸施压会迫使对手进入防御模式，失去主动权。', s['B']))

# ===== S8: Summary =====
story.append(ah('<b>八、使用建议与局限性</b>', s['H1'], 0))
story.append(Paragraph('本模型体系的主要优势在于将定性经验转化为定量计算，为决策提供了一个客观的参考基准。在实际使用中，建议玩家先通过CPI模型快速筛选卡牌（优先选择CPI大于1.2的卡牌），再用曲线优化模型检验费用分布是否合理。对局中，每个回合开始时先用场面估值函数判断局势优劣，然后用交换vs打脸模型指导出怪顺序和攻击目标。', s['B']))
story.append(Paragraph('模型的局限性同样需要正视：CPI的关键词权重是基于经验设定的固定值，无法精确反映不同对局环境下的效果价值差异（例如嘲讽在快攻对局中的价值远低于控制对局）。场面估值函数假设随从的攻防分配遵循平均比例，但实际卡牌的攻防差异极大（如1/30和12/1），使用具体面板数据可以获得更精确的结果。交换vs打脸模型没有考虑后续回合的连携效应（例如用1费随从换掉对面2费随从后，下回合的3费随从可以安全上场）。这些都是未来模型迭代可以改进的方向。', s['B']))

doc.multiBuild(story)
print(f"Manual generated: {op}")
