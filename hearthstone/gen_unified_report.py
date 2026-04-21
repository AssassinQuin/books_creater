# -*- coding: utf-8 -*-
import sys, os, hashlib
sys.path.insert(0, '/home/z/my-project/skills/pdf/scripts')
from pdf import install_font_fallback

import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                 Table, TableStyle, Image, CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

pdfmetrics.registerFont(TTFont('Microsoft YaHei', '/usr/share/fonts/truetype/chinese/msyh.ttf'))
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))
registerFontFamily('Microsoft YaHei', normal='Microsoft YaHei', bold='Microsoft YaHei')
registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
install_font_fallback()

ACCENT = colors.HexColor('#ce364f')
ACCENT2 = colors.HexColor('#e67e22')
TEXT_PRIMARY = colors.HexColor('#242220')
TEXT_MUTED = colors.HexColor('#807b73')
BG_SURFACE = colors.HexColor('#dfdcd7')
TABLE_HEADER_COLOR = ACCENT
TABLE_HEADER_TEXT = colors.white

with open('/home/z/my-project/hearthstone/full_model_data.json', 'r') as f:
    data = json.load(f)

PAGE_W, PAGE_H = A4
LM = RM = 1.0 * inch
TM = BM = 0.8 * inch
AW = PAGE_W - LM - RM

h1 = ParagraphStyle(name='H1', fontName='Microsoft YaHei', fontSize=20, leading=28, textColor=TEXT_PRIMARY, spaceBefore=18, spaceAfter=12, alignment=TA_LEFT, wordWrap='CJK')
h2 = ParagraphStyle(name='H2', fontName='Microsoft YaHei', fontSize=15, leading=22, textColor=ACCENT, spaceBefore=14, spaceAfter=8, alignment=TA_LEFT, wordWrap='CJK')
h3 = ParagraphStyle(name='H3', fontName='Microsoft YaHei', fontSize=12, leading=18, textColor=ACCENT2, spaceBefore=10, spaceAfter=6, alignment=TA_LEFT, wordWrap='CJK')
body = ParagraphStyle(name='Body', fontName='SimHei', fontSize=10.5, leading=18, textColor=TEXT_PRIMARY, spaceBefore=0, spaceAfter=6, alignment=TA_LEFT, wordWrap='CJK', firstLineIndent=21)
cap = ParagraphStyle(name='Cap', fontName='SimHei', fontSize=9, leading=14, textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=3, spaceAfter=6, wordWrap='CJK')
hc = ParagraphStyle(name='HC', fontName='SimHei', fontSize=9.5, leading=14, textColor=colors.white, alignment=TA_CENTER, wordWrap='CJK')
dc = ParagraphStyle(name='DC', fontName='SimHei', fontSize=9, leading=14, textColor=TEXT_PRIMARY, alignment=TA_CENTER, wordWrap='CJK')
dcl = ParagraphStyle(name='DCL', fontName='SimHei', fontSize=9, leading=14, textColor=TEXT_PRIMARY, alignment=TA_LEFT, wordWrap='CJK')

NEW_SET = {'残骸','黑暗之赐','灌注','扰魔','回溯','兆示','休眠','复生','奇闻','裂变','延系'}

class TocDocTemplate(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if hasattr(flowable, 'bookmark_name'):
            self.notify('TOCEntry', (getattr(flowable, 'bookmark_level', 0), getattr(flowable, 'bookmark_text', ''), self.page, getattr(flowable, 'bookmark_key', '')))

def heading(text, style, level=0):
    key = 'h_%s' % hashlib.md5(text.encode()).hexdigest()[:8]
    p = Paragraph('<a name="%s"/><b>%s</b>' % (key, text), style)
    p.bookmark_name = text; p.bookmark_level = level; p.bookmark_text = text; p.bookmark_key = key
    return p

def tbl(rows, cw):
    t = Table(rows, colWidths=cw, hAlign='CENTER')
    cmds = [('GRID',(0,0),(-1,-1),0.5,TEXT_MUTED),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('BACKGROUND',(0,0),(-1,0),TABLE_HEADER_COLOR),('TEXTCOLOR',(0,0),(-1,0),TABLE_HEADER_TEXT)]
    for i in range(1, len(rows)):
        cmds.append(('BACKGROUND',(0,i),(-1,i), colors.white if i%2==1 else BG_SURFACE))
    t.setStyle(TableStyle(cmds))
    return t

def img(path, max_w=AW, max_h=290):
    from reportlab.lib.utils import ImageReader
    im = Image(path)
    w, h = im.drawWidth, im.drawHeight
    r = min(max_w/w, max_h/h, 1.0)
    im.drawWidth, im.drawHeight = w*r, h*r
    return im

# ===== BUILD =====
out = '/home/z/my-project/download/hs_unified_body.pdf'
doc = TocDocTemplate(out, pagesize=A4, leftMargin=LM, rightMargin=RM, topMargin=TM, bottomMargin=BM)
story = []

# TOC
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle(name='TOC1', fontSize=12, leftIndent=20, fontName='SimHei', leading=22, spaceBefore=6),
    ParagraphStyle(name='TOC2', fontSize=10, leftIndent=40, fontName='SimHei', leading=18, spaceBefore=3),
]
story.append(Paragraph('<b>目  录</b>', ParagraphStyle(name='TT', fontName='Microsoft YaHei', fontSize=22, leading=30, textColor=TEXT_PRIMARY, alignment=TA_CENTER, spaceBefore=20, spaceAfter=20)))
story.append(toc)
story.append(PageBreak())

# ===== 一、数据总览 =====
story.append(heading('一、数据总览与模型重构', h1, 0))
story.append(Spacer(1, 6))
b = data['baseline']
story.append(Paragraph(
    '本报告基于2026年4月最新标准模式卡牌数据，完成了一次完整的关键词体系重构。此前分析仅基于卡牌的mechanics标签，'
    '遗漏了11种以文本描述形式呈现的新机制关键词。重构后的统一模型涵盖<b>35种关键词</b>，合计产生<b>933次</b>卡牌引用，'
    '覆盖了973张标准可收集卡牌中的约770张(79.1%%)。模型基于费用-属性线性回归基线(E=1.96C)，'
    '从数量分布、属性效率、机制分类、费用结构、职业特征和组合策略六个维度进行综合量化。', body))

# 核心指标
story.append(heading('1.1 核心指标概览', h2, 1))
story.append(Paragraph(
    '全体607张随从的平均费用为%.2f，平均总属性为%.1f，基于E=1.96C模型的平均效率差为%.3f。'
    '传统关键词产生%d次引用，新机制产生%d次引用，新机制占比%.1f%%。'
    '在新机制中，残骸(23张)、黑暗之赐(20张)、灌注(19张)位居前三，'
    '分别代表了"资源积累型"、"条件增益型"和"技能强化型"三种全新的机制设计方向。'
    % (b['avg_cost'], b['avg_stats'], b['efficiency'], b['old_kw_refs'], b['new_kw_refs'], b['new_kw_refs']*100/b['total_kw_refs']), body))

# 图1
story.append(Spacer(1, 8))
story.append(img('/home/z/my-project/download/fig1_full_kw_ranking.png', max_h=270))
story.append(Paragraph('图1 完整关键词排名TOP20（橙色=新机制 | 蓝色=传统机制）', cap))

# ===== 二、统一效率模型 =====
story.append(Spacer(1, 18))
story.append(heading('二、统一效率模型', h1, 0))
story.append(Spacer(1, 6))
story.append(Paragraph(
    '统一效率模型将所有关键词纳入同一评估框架。效率差值 = (实际总属性 - 1.96 x 费用) / 费用，'
    '正值表示该关键词卡的面板高于模型预测（面板溢价），负值表示面板低于预测（为机制效果付出代价）。'
    '模型揭示了关键词设计的核心逻辑：具有"负面机制约束"的关键词(如冲锋不能攻击英雄、过载锁费)获得面板溢价，'
    '而具有"正面额外效果"的关键词(如圣盾完全挡伤、剧毒击杀保证)需要削减面板来平衡。', body))

story.append(heading('2.1 效率差值全景', h2, 1))
story.append(Paragraph(
    '效率最高的关键词梯队：冲锋(+2.44，4张)因"不能攻击英雄"的严重限制获得最高面板溢价；'
    '过载(+1.73，4张)因下回合锁费获得高额补偿；'
    '<b>休眠(+1.14，11张)</b>是效率最高的新机制——打出后需等待数回合才能行动，'
    '因此获得了远超常规的面板属性，休眠随从的平均属性(9.7)远高于同费用(3.55费)的基线期望(6.96)。', body))
story.append(Paragraph(
    '效率接近平衡线的关键词：发现(+0.006)、嘲讽(-0.027)、战吼(-0.033)的效率差接近于零，'
    '说明这些机制的设计已经达到了面板与效果的精妙平衡。<b>扰魔(+0.003)</b>作为新机制也接近平衡线，'
    '反映了法术免疫机制的成本已被精确计算并体现在面板中。', body))
story.append(Paragraph(
    '效率最低的关键词梯队：剧毒(-0.58)、重生(-0.53)、圣盾(-0.48)和复生(-0.50，新机制)的面板亏损最大。'
    '<b>兆示(-0.40，7张)</b>和<b>回溯(-0.39，10张)</b>作为新机制也处于高亏损区间——'
    '兆示在手牌中持续提供价值但不占场面，回溯的双轨效果提供了远超单效果卡的灵活性。'
    '<b>黑暗之赐(-0.11)</b>的亏损相对温和，因其增益需要条件触发而非立即生效。', body))

story.append(Spacer(1, 8))
story.append(img('/home/z/my-project/download/fig2_unified_efficiency.png', max_h=310))
story.append(Paragraph('图2 统一关键词属性效率模型全景（橙=新机制 | 红=超模 | 蓝=亏模）', cap))

# 效率表
story.append(heading('2.2 完整效率数据表', h2, 1))
eff = data['kw_efficiency']
rows = [[Paragraph('<b>关键词</b>', hc), Paragraph('<b>类型</b>', hc), Paragraph('<b>效率差</b>', hc),
         Paragraph('<b>数量</b>', hc), Paragraph('<b>均费</b>', hc), Paragraph('<b>均属性</b>', hc)]]
for name, d in sorted(eff.items(), key=lambda x: -x[1]['eff_vs_baseline']):
    typ = '新' if name in NEW_SET else '旧'
    sign = '+' if d['eff_vs_baseline'] >= 0 else ''
    rows.append([Paragraph(name, dcl), Paragraph(typ, dc), Paragraph('%s%.3f' % (sign, d['eff_vs_baseline']), dc),
                 Paragraph(str(d['count']), dc), Paragraph('%.2f' % d['avg_cost'], dc), Paragraph('%.1f' % d['avg_stats'], dc)])
cw = [AW*0.20, AW*0.08, AW*0.16, AW*0.12, AW*0.14, AW*0.14]
story.append(Spacer(1, 10))
story.append(tbl(rows, cw))
story.append(Paragraph('表1 完整关键词属性效率数据', cap))

# ===== 三、机制分类体系 =====
story.append(Spacer(1, 18))
story.append(heading('三、机制分类体系与维度分析', h1, 0))
story.append(Spacer(1, 6))
story.append(Paragraph(
    '为建立系统化的关键词认知框架，本报告将35种关键词按六个核心维度进行分类：'
    '<b>攻击性</b>（直接提升伤害输出能力）、<b>防御性</b>（减少或规避敌方伤害）、'
    '<b>资源性</b>（提供额外资源或资源转换）、<b>灵活性</b>（提供选择或多路径决策）、'
    '<b>触发性</b>（被动自动触发效果）和<b>条件性</b>（需要满足特定条件才能激活）。'
    '每个关键词在这六个维度上的评分(0-5)构成了其"机制指纹"。', body))

story.append(Paragraph(
    '传统机制中，冲锋(攻击5)和突袭(攻击5)是纯攻击型关键词；嘲讽(防御5)和圣盾(防御5)是纯防御型；'
    '发现(灵活5)是最具弹性的传统机制。新机制展现了更复杂的多维特征：'
    '残骸(资源5, 条件2)需要主动管理第三资源；兆示(条件5)完全依赖条件满足；'
    '灌注(灵活4, 资源3)通过升级英雄技能创造多路线策略；'
    '裂变(灵活4, 条件2)需要双卡配合才能发挥；回溯(灵活5)提供了双轨选择的最大化决策空间。'
    '这种多维分类体系为后续的构筑决策和对局评估提供了量化工具。', body))

story.append(Spacer(1, 8))
story.append(img('/home/z/my-project/download/fig3_radar_classification.png', max_h=310))
story.append(Paragraph('图3 关键词机制维度分类雷达图（实线=新机制 | 虚线=传统机制）', cap))

# ===== 四、多关键词组合 =====
story.append(Spacer(1, 18))
story.append(heading('四、多关键词组合分析', h1, 0))
story.append(Spacer(1, 6))
story.append(Paragraph(
    '在新旧机制融合的背景下，多关键词组合呈现出更丰富的策略维度。嘲讽+战吼(20张)保持第一，'
    '体现了"防御+主动触发"的经典搭配。发现+战吼从纯传统组合(25张)变为包含黑暗之赐的复合组合(16张)，'
    '因为大量"发现具有黑暗之赐的卡牌"同时具备发现和战吼标签。', body))
story.append(Paragraph(
    '新机制催生的特色组合包括：战吼+灌注(8张)——打出时强化英雄技能；'
    '回溯+战吼(7张)——双轨选择+即时触发；发现+黑暗之赐(6张)——择取增益型卡牌；'
    '战吼+残骸(5张)——死亡骑士的资源消耗触发链；奇闻+战吼(5张)——传说级效果的主动触发；'
    '兆示+战吼(4张)——条件预置+即时效果。这些组合多数围绕战吼展开，'
    '说明战吼作为"打出即触发"的基础框架，是承载其他机制效果的最佳载体。', body))

story.append(Spacer(1, 8))
story.append(img('/home/z/my-project/download/fig4_combo_ranking.png', max_h=250))
story.append(Paragraph('图4 多关键词组合排名TOP15（橙色=含新机制 | 蓝色=纯传统）', cap))

# ===== 五、职业分析 =====
story.append(Spacer(1, 18))
story.append(heading('五、职业关键词特征分析', h1, 0))
story.append(Spacer(1, 6))

story.append(Paragraph(
    '统一模型下的职业分析揭示了新旧机制如何重塑各职业的策略身份。死亡骑士以残骸(22)+复生(5)'
    '=27次新机制引用遥遥领先，加上24次战吼和10次亡语，形成了"残骸积累-亡语触发-复生循环"的'
    '完全独立运作体系，其对局逻辑与传统十职业有本质区别。', body))
story.append(Paragraph(
    '术士(22次战吼+10次亡语+4次黑暗之赐)保持了"高战吼密度+属性增益"的设计路线。'
    '战士(21次战吼+5次嘲讽+3次黑暗之赐)的新机制融入相对温和。'
    '潜行者(19次战吼+9次连击+3次黑暗之赐+2次兆示)展现了最丰富的机制多样性——连击的固定路线与兆示的概率路线并存，'
    '加上黑暗之赐的属性增益，构成了多层次的策略选择。德鲁伊(12次战吼+9次抉择+3次扰魔)继续保持"灵活选择"的职业核心，'
    '扰魔的法术免疫为其提供了独特的反法术手段。', body))

story.append(Spacer(1, 8))
story.append(img('/home/z/my-project/download/fig5_full_class_heatmap.png', max_h=280))
story.append(Paragraph('图5 各职业完整关键词分布热力图', cap))

# 职业表
story.append(heading('5.1 职业关键词签名', h2, 1))
cls_data = [
    ('死亡骑士', '81', '战吼(24)+残骸(22)+亡语(10)', '残骸资源独立体系'),
    ('术士', '64', '战吼(22)+亡语(10)+黑暗之赐(4)', '高战吼+增益传播'),
    ('战士', '64', '战吼(21)+嘲讽(5)+黑暗之赐(3)', '战吼密度+防御增益'),
    ('牧师', '64', '战吼(20)+吸血(8)+扰魔(2)', '回复+法术免疫'),
    ('潜行者', '64', '战吼(19)+连击(9)+黑暗之赐(3)', '连击+兆示+增益'),
    ('圣骑士', '66', '战吼(17)+圣盾(7)+嘲讽(6)', '圣盾双保体系'),
    ('萨满', '64', '战吼(16)+过载(10)+兆示(2)', '过载节奏+条件触发'),
    ('猎人', '64', '战吼(15)+亡语(7)+奥秘(5)', '战吼密度+奥秘控场'),
    ('恶魔猎手', '64', '战吼(14)+突袭(7)+休眠(5)', '突袭+延迟部署'),
    ('德鲁伊', '64', '战吼(12)+抉择(9)+扰魔(3)', '抉择+法术免疫'),
    ('法师', '64', '战吼(14)+发现(7)+奥秘(5)', '发现择取+奥秘'),
    ('中立', '250', '战吼(113)+亡语(37)+嘲讽(31)', '通用功能卡'),
]
rows = [[Paragraph('<b>职业</b>', hc), Paragraph('<b>卡数</b>', hc), Paragraph('<b>关键词签名</b>', hc), Paragraph('<b>策略特征</b>', hc)]]
for c, n, sig, feat in cls_data:
    rows.append([Paragraph(c, dc), Paragraph(n, dc), Paragraph(sig, dcl), Paragraph(feat, dcl)])
cw2 = [AW*0.14, AW*0.10, AW*0.44, AW*0.32]
story.append(Spacer(1, 10))
story.append(tbl(rows, cw2))
story.append(Paragraph('表2 各职业完整关键词签名', cap))

# ===== 六、决策模型 =====
story.append(Spacer(1, 18))
story.append(heading('六、统一决策模型', h1, 0))
story.append(Spacer(1, 6))

story.append(Paragraph(
    '基于完整关键词体系，决策模型升级为三层架构：底层为面板效率层(E=1.96C模型)，'
    '中层为机制价值层(六维评分体系)，顶层为对局策略层(流派匹配与费用曲线)。',
    body))

story.append(heading('6.1 机制价值层量化规则', h2, 1))
story.append(Paragraph(
    '每个关键词的"隐性机制价值"可通过效率差值的绝对值来量化。效率差为正的关键词(面板溢价)意味着'
    '"机制约束价值 = 面板溢价量"：冲锋的+2.44意味着每费约2.44点属性的超额提供是对"不能攻击英雄"的精确补偿，'
    '实际评估冲锋卡时应将这部分溢价视为机制约束成本而非收益。'
    '效率差为负的关键词(机制代价)意味着"机制效果价值 = 面板亏损量 + 基线属性"：'
    '圣盾的-0.48意味着每费约0.48点属性被转移为圣盾效果，一张5费圣盾随从的实际价值 = '
    '面板属性(7.2) + 圣盾效果(约2.4) = 9.6，远超5费基线(9.8)，但因圣盾效果是一次性的，'
    '其长期价值需根据对局阶段动态评估。', body))

story.append(heading('6.2 新机制价值评估要点', h2, 1))
story.append(Paragraph(
    '<b>残骸(效率差-0.087)：</b>面板亏损轻微但残骸资源的持续积累价值巨大。'
    '一场10回合的对局中，高效的残骸套牌可积累20-30份残骸，足以触发多次复生或强化效果。'
    '残骸卡的对局价值 = 面板属性 + 残骸产出率 x 预期存活回合数。', body))
story.append(Paragraph(
    '<b>兆示(效率差-0.395)：</b>面板亏损较大，但兆示卡的核心价值在于"不占牌面资源就能持续积累优势"。'
    '一张3费兆示卡在手牌中可能持续3-4回合后触发一次4费等值效果，相当于净赚1费+额外价值。'
    '对局评估时应将兆示的"免费触发回合"计算在内。', body))
story.append(Paragraph(
    '<b>灌注(效率差-0.084)：</b>面板亏损温和，但强化英雄技能的收益是持续性且累积性的。'
    '灌注后的英雄技能每回合都能提供额外效果，5回合的累积价值远超单次战吼效果。'
    '中速套牌应优先在3-5费段打出灌注卡，以最大化强化后英雄技能的使用次数。', body))
story.append(Paragraph(
    '<b>黑暗之赐(效率差-0.109)：</b>面板亏损可控，但增益的传播性和永久性使其在中后期极具价值。'
    '通过"发现具有黑暗之赐的卡牌"实现增益传播，一套牌中可能同时存在3-4张获得黑暗之赐增益的随从，'
    '形成指数级属性膨胀。对局中应优先保留具有黑暗之赐发现效果的卡牌，'
    '在对手解场能力不足的中后期打出以建立不可逆的属性优势。', body))
story.append(Paragraph(
    '<b>回溯(效率差-0.393)：</b>面板亏损较大，但双轨选择的价值在于信息不对称和灵活性溢价。'
    '回溯卡的期望价值约为单效果卡的1.5倍(考虑对手无法预判你的选择)。'
    '对战控制套牌时应倾向于选择保守效果(如过牌、防御)，对战快攻时选择激进效果(如直伤、场面)。', body))

# 新旧对比图
story.append(Spacer(1, 8))
story.append(img('/home/z/my-project/download/fig6_new_old_set.png', max_h=240))
story.append(Paragraph('图6 新旧机制占比及各卡组贡献', cap))

# 最终矩阵
story.append(heading('6.3 完整流派关键词偏好矩阵', h2, 1))
rows = [[Paragraph('<b>流派</b>', hc), Paragraph('<b>传统关键词</b>', hc), Paragraph('<b>新机制关键词</b>', hc), Paragraph('<b>费用曲线</b>', hc)]]
arch = [
    ('快攻', '突袭、圣盾、风怒、冲锋', '兆示(低费)、休眠', '1~3费密集'),
    ('中速', '战吼、发现、嘲讽', '灌注、回溯、黑暗之赐', '3~6费核心'),
    ('控制', '亡语、吸血、嘲讽', '残骸、复生、扰魔', '5~8费高价值'),
    ('组合', '战吼、发现、任务', '裂变、奇闻、兆示', '全费用段搜索'),
]
for a, old, new, cost in arch:
    rows.append([Paragraph(a, dc), Paragraph(old, dcl), Paragraph(new, dcl), Paragraph(cost, dc)])
cw3 = [AW*0.12, AW*0.30, AW*0.34, AW*0.24]
story.append(Spacer(1, 10))
story.append(tbl(rows, cw3))
story.append(Paragraph('表3 完整流派关键词偏好矩阵（传统+新机制）', cap))

doc.multiBuild(story)
print(f"Unified PDF: {out}")
import os
print(f"Size: {os.path.getsize(out)/1024:.1f} KB")
