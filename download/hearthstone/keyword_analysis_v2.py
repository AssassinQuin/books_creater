#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
炉石传说标准模式 —— 全关键词中和分析 v2.0
包含新扩展包关键词：兆示、灌注、黑暗之赐、流放、回溯、延系、扰魔、裂变、残骸、奇闻、休眠等
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from collections import Counter
import re
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 0. 字体配置
# ============================================================
fm.fontManager.addfont('/usr/share/fonts/truetype/chinese/SimHei.ttf')
fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

OUTDIR = '/home/z/my-project/download/hearthstone'

# ============================================================
# 1. 数据加载与预处理
# ============================================================
print("=" * 60)
print("炉石传说标准模式 —— 全关键词中和分析 v2.0")
print("=" * 60)

with open(f'{OUTDIR}/cards_zh.json', 'r') as f:
    all_cards = json.load(f)

STD_SETS = ['CORE', 'CATACLYSM', 'EMERALD_DREAM', 'THE_LOST_CITY', 'TIME_TRAVEL']
SET_NAMES_CN = {
    'CORE': '核心',
    'CATACLYSM': '大灾变',
    'EMERALD_DREAM': '翡翠梦境',
    'THE_LOST_CITY': '失落之城',
    'TIME_TRAVEL': '时光之裂'
}

CLASS_CN = {
    'DEMONHUNTER': '恶魔猎手', 'DRUID': '德鲁伊', 'HUNTER': '猎人',
    'MAGE': '法师', 'PALADIN': '圣骑士', 'PRIEST': '牧师',
    'ROGUE': '盗贼', 'SHAMAN': '萨满', 'WARLOCK': '术士',
    'WARRIOR': '战士', 'NEUTRAL': '中立', 'DEATHKNIGHT': '死亡骑士'
}

# 筛选标准可收集卡牌
cards = []
for c in all_cards:
    if c.get('set') in STD_SETS and c.get('collectible', False):
        # 过滤地标和英雄牌（不适合数值建模）
        if c.get('type') in ['HERO', 'LOCATION', 'BATTLEGROUND']:
            continue
        cards.append(c)

print(f"标准模式可收集卡牌: {len(cards)} 张")

# 提取关键字段
df = pd.DataFrame(cards)
df = df[['name', 'cardClass', 'set', 'cost', 'attack', 'health', 'type', 'rarity', 'text', 'mechanics', 'spellSchool']]
df.columns = ['名称', '职业', '系列', '费用', '攻击', '生命', '类型', '稀有度', '文本', '机制', '学派']
df['费用'] = pd.to_numeric(df['费用'], errors='coerce').fillna(0).astype(int)
df['攻击'] = pd.to_numeric(df['攻击'], errors='coerce').fillna(0).astype(int)
df['生命'] = pd.to_numeric(df['生命'], errors='coerce').fillna(0).astype(int)
df['职业CN'] = df['职业'].map(CLASS_CN).fillna('其他')
df['系列CN'] = df['系列'].map(SET_NAMES_CN).fillna('其他')
df['文本'] = df['文本'].fillna('')

# 随从牌子集（用于属性效率分析）
df_minion = df[df['类型'] == 'MINION'].copy()

# ============================================================
# 2. 关键词定义（完整版 —— 包含新扩展包机制）
# ============================================================

# 核心战斗关键词
CORE_COMBAT = {
    '嘲讽': '嘲讽',
    '突袭': '突袭',
    '圣盾': '圣盾',
    '潜行': '潜行',
    '风怒': '风怒',
    '吸血': '吸血',
    '剧毒': '剧毒',
    '冻结': '冻结',
    '免疫': '免疫',
    '冲锋': '冲锋',
    '复生': '复生',
    '沉默': '沉默',
}

# 触发类关键词
TRIGGER_KW = {
    '战吼': '战吼',
    '亡语': '亡语',
    '过载': '过载',
    '连击': '连击',
}

# 新扩展包机制关键词（用户要求补充）
NEW_MECHANICS = {
    '兆示': '兆示 (Foretell)',     # 用户称"昭示"，正式名为"兆示"
    '灌注': '灌注 (Infuse)',
    '黑暗之赐': '黑暗之赐 (Dark Gift)',
    '流放': '流放 (Outcast)',
    '回溯': '回溯 (Recall)',
    '延系': '延系 (Reverberate)',
    '扰魔': '扰魔 (Disruptor)',
    '裂变': '裂变 (Fission)',
    '残骸': '残骸 (Corpses)',
    '奇闻': '奇闻 (Marvel)',
    '休眠': '休眠 (Dormant)',
    '可交易': '可交易 (Tradeable)',
    '抉择': '抉择 (Choose One)',
}

ALL_KEYWORDS = {}
ALL_KEYWORDS.update(CORE_COMBAT)
ALL_KEYWORDS.update(TRIGGER_KW)
ALL_KEYWORDS.update(NEW_MECHANICS)

print(f"\n关键词总数: {len(ALL_KEYWORDS)}")
print(f"  核心战斗: {len(CORE_COMBAT)}")
print(f"  触发类: {len(TRIGGER_KW)}")
print(f"  新机制: {len(NEW_MECHANICS)}")

# ============================================================
# 3. 关键词检测
# ============================================================

def detect_keywords(text):
    """检测卡牌文本中的关键词"""
    found = {}
    for kw, label in ALL_KEYWORDS.items():
        # 使用<b>标签精确匹配，或纯文本匹配（带边界保护）
        if kw in text:
            found[kw] = label
    return found

# 为每张卡牌检测关键词
df['关键词列表'] = df['文本'].apply(detect_keywords)
df['关键词数'] = df['关键词列表'].apply(len)
df['有关键词'] = df['关键词数'] > 0

# 统计每个关键词出现次数
kw_counts = Counter()
for kw_dict in df['关键词列表']:
    for kw in kw_dict:
        kw_counts[kw] += 1

print("\n=== 关键词出现次数（按频次排序）===")
for kw, cnt in kw_counts.most_common():
    label = ALL_KEYWORDS[kw]
    print(f"  {label}: {cnt} 张")

# ============================================================
# 4. 效率评分模型 E = 1.96C
# ============================================================

def calc_efficiency(row):
    """计算卡牌属性效率 = (攻击 + 生命) / (1.96 * 费用)"""
    cost = row['费用']
    if cost <= 0:
        return 0.0
    total_stat = row['攻击'] + row['生命']
    expected = 1.96 * cost
    return total_stat / expected if expected > 0 else 0

df['属性效率'] = df.apply(calc_efficiency, axis=1)

# 随从子集也需效率列
df_minion = df[df['类型'] == 'MINION'].copy()

# ============================================================
# 5. 分析一：关键词分布分析
# ============================================================
print("\n\n>>> 分析一：关键词分布分析")

kw_dist = pd.DataFrame([
    {'关键词': kw, '标签': ALL_KEYWORDS[kw], '卡牌数': cnt}
    for kw, cnt in kw_counts.most_common()
])

# 按类别分组
kw_dist['类别'] = kw_dist['关键词'].apply(
    lambda x: '核心战斗' if x in CORE_COMBAT else ('触发类' if x in TRIGGER_KW else '新机制')
)

# 图1：关键词分布横向柱状图（按类别分组）
fig, ax = plt.subplots(figsize=(14, 10))
cats = ['核心战斗', '新机制', '触发类']
colors_map = {'核心战斗': '#e74c3c', '新机制': '#2ecc71', '触发类': '#3498db'}
y_pos = 0
y_labels = []
y_colors = []
y_vals = []
for cat in cats:
    subset = kw_dist[kw_dist['类别'] == cat].sort_values('卡牌数', ascending=True)
    for _, row in subset.iterrows():
        y_labels.append(row['标签'])
        y_colors.append(colors_map[cat])
        y_vals.append(row['卡牌数'])
        y_pos += 1
    if cat != cats[-1]:
        y_pos += 0.5  # 类别间留空

bars = ax.barh(range(len(y_labels)), y_vals, color=y_colors, edgecolor='white', height=0.7)
ax.set_yticks(range(len(y_labels)))
ax.set_yticklabels(y_labels, fontsize=11)
ax.set_xlabel('卡牌数量', fontsize=13)
ax.set_title('标准模式全关键词分布（含新扩展包机制）', fontsize=16, fontweight='bold')

# 添加数值标签
for bar, val in zip(bars, y_vals):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
            str(val), va='center', fontsize=10, fontweight='bold')

# 添加图例
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=c, label=l) for l, c in colors_map.items()]
ax.legend(handles=legend_elements, loc='lower right', fontsize=12)
ax.set_xlim(0, max(y_vals) * 1.15)
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart01_keyword_distribution.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图1: chart01_keyword_distribution.png 已保存")

# 图2：新机制关键词详细分布（独立饼图）
new_kw_data = kw_dist[kw_dist['类别'] == '新机制'].sort_values('卡牌数', ascending=False)
fig, ax = plt.subplots(figsize=(10, 8))
wedges, texts, autotexts = ax.pie(
    new_kw_data['卡牌数'], labels=new_kw_data['标签'],
    autopct='%1.1f%%', pctdistance=0.8,
    colors=sns.color_palette('Set2', len(new_kw_data)),
    startangle=90, textprops={'fontsize': 11}
)
for at in autotexts:
    at.set_fontsize(10)
    at.set_fontweight('bold')
ax.set_title('新扩展包机制关键词分布', fontsize=15, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart02_new_mechanics_pie.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图2: chart02_new_mechanics_pie.png 已保存")

# ============================================================
# 6. 分析二：关键词效率分析
# ============================================================
print("\n>>> 分析二：关键词效率分析")

df_eff = df_minion.copy()  # 只分析随从

eff_data = []
for kw, label in ALL_KEYWORDS.items():
    has_kw = df_eff[df_eff['文本'].str.contains(kw, na=False)]
    no_kw = df_eff[~df_eff['文本'].str.contains(kw, na=False)]
    if len(has_kw) >= 3:  # 至少3张卡才分析
        eff_data.append({
            '关键词': label,
            '数量': len(has_kw),
            '有关键词效率': round(has_kw['属性效率'].mean(), 3),
            '无关键词效率': round(no_kw['属性效率'].mean(), 3),
            '效率差': round(has_kw['属性效率'].mean() - no_kw['属性效率'].mean(), 3),
            '有关键词攻击': round(has_kw['攻击'].mean(), 2),
            '有关键词生命': round(has_kw['生命'].mean(), 2),
            '平均费用': round(has_kw['费用'].mean(), 2),
        })

df_eff_summary = pd.DataFrame(eff_data).sort_values('效率差', ascending=True)

# 图3：关键词效率对比图
fig, ax = plt.subplots(figsize=(14, 10))
y_pos = range(len(df_eff_summary))
labels = df_eff_summary['关键词'].values
vals_with = df_eff_summary['有关键词效率'].values
vals_without = df_eff_summary['无关键词效率'].values
diffs = df_eff_summary['效率差'].values

colors = ['#e74c3c' if d < 0 else '#2ecc71' for d in diffs]
bars = ax.barh(y_pos, vals_with, color=colors, alpha=0.7, height=0.6, label='有关键词卡牌')
ax.axvline(x=df_eff['属性效率'].mean(), color='#f39c12', linestyle='--', linewidth=2, label=f'整体均值 ({df_eff["属性效率"].mean():.3f})')
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=10)
ax.set_xlabel('属性效率 (E)', fontsize=13)
ax.set_title('各关键词卡牌属性效率 vs 整体均值', fontsize=15, fontweight='bold')

for i, (bar, val, diff) in enumerate(zip(bars, vals_with, diffs)):
    sign = '+' if diff > 0 else ''
    ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
            f'{val:.3f} ({sign}{diff:.3f})', va='center', fontsize=9)

ax.legend(loc='lower right', fontsize=11)
ax.set_xlim(0, max(vals_with) * 1.3)
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart03_keyword_efficiency.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图3: chart03_keyword_efficiency.png 已保存")

# ============================================================
# 7. 分析三：关键词费用结构分析
# ============================================================
print("\n>>> 分析三：关键词费用结构分析")

# 图4：新机制关键词费用分布箱线图
fig, ax = plt.subplots(figsize=(14, 8))
new_kw_list = [kw for kw in NEW_MECHANICS.keys() if kw_counts.get(kw, 0) >= 3]
new_kw_labels = [NEW_MECHANICS[kw] for kw in new_kw_list]
box_data = []
box_labels = []
for kw in new_kw_list:
    subset = df[df['文本'].str.contains(kw, na=False)]['费用']
    if len(subset) >= 3:
        box_data.append(subset.values)
        box_labels.append(NEW_MECHANICS[kw])

bp = ax.boxplot(box_data, labels=box_labels, patch_artist=True, notch=True,
                medianprops=dict(color='black', linewidth=2))
colors_box = sns.color_palette('Set3', len(box_data))
for patch, color in zip(bp['boxes'], colors_box):
    patch.set_facecolor(color)
    patch.set_alpha(0.8)
ax.set_ylabel('法力值费用', fontsize=13)
ax.set_title('新机制关键词卡牌费用分布', fontsize=15, fontweight='bold')
ax.tick_params(axis='x', rotation=30, labelsize=10)
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart04_new_mechanics_cost.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图4: chart04_new_mechanics_cost.png 已保存")

# 图5：所有关键词费用热力图
cost_range = list(range(0, 11))
heat_data = []
heat_labels = []
for kw, label in ALL_KEYWORDS.items():
    if kw_counts.get(kw, 0) >= 5:
        subset = df[df['文本'].str.contains(kw, na=False)]
        cost_dist = []
        for cost in cost_range:
            cost_dist.append(len(subset[subset['费用'] == cost]))
        heat_data.append(cost_dist)
        heat_labels.append(label)

heat_df = pd.DataFrame(heat_data, index=heat_labels, columns=[str(c) for c in cost_range])
heat_df_norm = heat_df.div(heat_df.sum(axis=1), axis=0)  # 归一化

fig, ax = plt.subplots(figsize=(14, 10))
sns.heatmap(heat_df_norm, annot=heat_df.values, fmt='d', cmap='YlOrRd',
            linewidths=0.5, ax=ax, cbar_kws={'label': '占比'})
ax.set_xlabel('法力值费用', fontsize=13)
ax.set_ylabel('关键词', fontsize=13)
ax.set_title('关键词 × 费用分布热力图（数值=卡牌数，颜色=占比）', fontsize=15, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart05_keyword_cost_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图5: chart05_keyword_cost_heatmap.png 已保存")

# ============================================================
# 8. 分析四：新机制职业特征分析
# ============================================================
print("\n>>> 分析四：新机制职业特征分析")

# 计算每个职业对每个新关键词的使用频率
classes_all = ['恶魔猎手', '德鲁伊', '猎人', '法师', '圣骑士', '牧师', '盗贼', '萨满', '术士', '战士', '中立', '死亡骑士']
class_kw_matrix = pd.DataFrame(index=classes_all, columns=[NEW_MECHANICS[kw] for kw in new_kw_list], data=0.0)

for cls in classes_all:
    cls_cards = df[df['职业CN'] == cls]
    cls_total = len(cls_cards)
    if cls_total == 0:
        continue
    for kw in new_kw_list:
        count = len(cls_cards[cls_cards['文本'].str.contains(kw, na=False)])
        class_kw_matrix.loc[cls, NEW_MECHANICS[kw]] = round(count / cls_total * 100, 1)

# 图6：职业-新机制关键词雷达图（取前6个高频职业）
top_classes = df[df['职业CN'] != '中立']['职业CN'].value_counts().head(8).index.tolist()
top_new_kw = [NEW_MECHANICS[kw] for kw in new_kw_list[:8]]

fig, axes = plt.subplots(2, 4, figsize=(20, 10), subplot_kw=dict(polar=True))
angles = np.linspace(0, 2 * np.pi, len(top_new_kw), endpoint=False).tolist()
angles += angles[:1]

colors_cls = sns.color_palette('husl', len(top_classes))

for idx, cls in enumerate(top_classes):
    ax = axes.flat[idx]
    values = [class_kw_matrix.loc[cls, kw] if kw in class_kw_matrix.columns else 0 for kw in top_new_kw]
    values += values[:1]
    ax.fill(angles, values, alpha=0.2, color=colors_cls[idx])
    ax.plot(angles, values, 'o-', color=colors_cls[idx], linewidth=2, markersize=4)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(top_new_kw, fontsize=7, rotation=30)
    ax.set_title(cls, fontsize=12, fontweight='bold', pad=15)
    ax.set_ylim(0, max(class_kw_matrix[top_new_kw].max().max() * 1.2, 10))

plt.suptitle('各职业新机制关键词使用率雷达图（%）', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart06_class_radar_new.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图6: chart06_class_radar_new.png 已保存")

# ============================================================
# 9. 分析五：关键词组合分析
# ============================================================
print("\n>>> 分析五：关键词组合分析")

# 分析最常见的双关键词组合
combo_counter = Counter()
for kw_dict in df['关键词列表']:
    kws = list(kw_dict.keys())
    if len(kws) >= 2:
        for i in range(len(kws)):
            for j in range(i+1, len(kws)):
                combo = tuple(sorted([ALL_KEYWORDS[kws[i]], ALL_KEYWORDS[kws[j]]]))
                combo_counter[combo] += 1

# 图7：关键词组合热力图（含新关键词）
top_kws_all = [kw for kw, cnt in kw_counts.most_common(18)]
top_labels = [ALL_KEYWORDS[kw] for kw in top_kws_all]
combo_matrix = pd.DataFrame(0, index=top_labels, columns=top_labels)

for combo, cnt in combo_counter.most_common():
    if combo[0] in top_labels and combo[1] in top_labels:
        combo_matrix.loc[combo[0], combo[1]] = cnt
        combo_matrix.loc[combo[1], combo[0]] = cnt

fig, ax = plt.subplots(figsize=(16, 14))
mask = np.triu(np.ones_like(combo_matrix, dtype=bool), k=1)
sns.heatmap(combo_matrix, mask=mask, annot=True, fmt='d', cmap='Blues',
            linewidths=0.5, ax=ax, square=True,
            cbar_kws={'label': '同时出现次数'})
ax.set_title('关键词组合热力图（下三角）', fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart07_combo_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图7: chart07_combo_heatmap.png 已保存")

# ============================================================
# 10. 分析六：新机制深度分析
# ============================================================
print("\n>>> 分析六：新机制深度分析")

# 各新关键词详细数据表
new_kw_detail = []
for kw in new_kw_list:
    subset = df[df['文本'].str.contains(kw, na=False)]
    if len(subset) < 1:
        continue
    minion_sub = subset[subset['类型'] == 'MINION']
    spell_sub = subset[subset['类型'] == 'SPELL']
    new_kw_detail.append({
        '关键词': NEW_MECHANICS[kw],
        '总数': len(subset),
        '随从': len(minion_sub),
        '法术': len(spell_sub),
        '其他': len(subset) - len(minion_sub) - len(spell_sub),
        '平均费用': round(subset['费用'].mean(), 2),
        '主要职业': subset['职业CN'].mode().iloc[0] if len(subset) > 0 else '-',
        '涉及职业数': subset['职业CN'].nunique(),
        '系列分布': ', '.join(subset['系列CN'].value_counts().head(3).index.tolist()),
    })

df_new_detail = pd.DataFrame(new_kw_detail)
print("\n新机制关键词详细数据:")
print(df_new_detail.to_string(index=False))

# 图8：新机制卡牌类型分布堆叠柱状图
fig, ax = plt.subplots(figsize=(14, 7))
kw_names = df_new_detail['关键词'].values
x = np.arange(len(kw_names))
width = 0.6

p1 = ax.bar(x, df_new_detail['随从'].values, width, label='随从', color='#3498db')
p2 = ax.bar(x, df_new_detail['法术'].values, width, bottom=df_new_detail['随从'].values, label='法术', color='#e74c3c')
p3 = ax.bar(x, df_new_detail['其他'].values, width,
            bottom=(df_new_detail['随从'].values + df_new_detail['法术'].values), label='其他', color='#95a5a6')

for i, total in enumerate(df_new_detail['总数'].values):
    ax.text(i, total + 0.3, str(total), ha='center', fontweight='bold', fontsize=11)

ax.set_xticks(x)
ax.set_xticklabels(kw_names, fontsize=10, rotation=20)
ax.set_ylabel('卡牌数量', fontsize=13)
ax.set_title('新机制关键词 —— 卡牌类型分布', fontsize=15, fontweight='bold')
ax.legend(loc='best', fontsize=11)
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart08_new_mechanics_types.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图8: chart08_new_mechanics_types.png 已保存")

# ============================================================
# 11. 分析七：系列关键词分布
# ============================================================
print("\n>>> 分析七：系列关键词分布")

set_kw_matrix = pd.DataFrame(0, index=list(SET_NAMES_CN.values()), columns=[ALL_KEYWORDS[kw] for kw in top_kws_all])

for set_en, set_cn in SET_NAMES_CN.items():
    set_cards = df[df['系列'] == set_en]
    for kw in top_kws_all:
        count = len(set_cards[set_cards['文本'].str.contains(kw, na=False)])
        set_kw_matrix.loc[set_cn, kw] = count

# 图9：系列 × 关键词热力图
fig, ax = plt.subplots(figsize=(18, 6))
sns.heatmap(set_kw_matrix.astype(int), annot=True, fmt='d', cmap='YlGnBu',
            linewidths=0.5, ax=ax, cbar_kws={'label': '卡牌数'})
ax.set_xlabel('关键词', fontsize=13)
ax.set_ylabel('扩展包', fontsize=13)
ax.set_title('各扩展包关键词分布热力图', fontsize=15, fontweight='bold')
ax.tick_params(axis='x', rotation=40, labelsize=9)
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart09_set_keyword_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图9: chart09_set_keyword_heatmap.png 已保存")

# ============================================================
# 12. 图10：新机制随从效率对比柱状图
# ============================================================
print("\n>>> 新机制随从效率对比")

new_eff_data = []
for kw in new_kw_list:
    label = NEW_MECHANICS[kw]
    minion_sub = df_minion[df_minion['文本'].str.contains(kw, na=False)]
    if len(minion_sub) >= 2:
        new_eff_data.append({
            '关键词': label,
            '数量': len(minion_sub),
            '平均效率': round(minion_sub['属性效率'].mean(), 3),
            '平均攻击': round(minion_sub['攻击'].mean(), 2),
            '平均生命': round(minion_sub['生命'].mean(), 2),
            '平均费用': round(minion_sub['费用'].mean(), 2),
            '最大效率': round(minion_sub['属性效率'].max(), 3),
            '最小效率': round(minion_sub['属性效率'].min(), 3),
        })

df_new_eff = pd.DataFrame(new_eff_data).sort_values('平均效率', ascending=True)

fig, ax = plt.subplots(figsize=(12, 7))
labels = df_new_eff['关键词'].values
vals = df_new_eff['平均效率'].values
colors = ['#e74c3c' if v < df_minion['属性效率'].mean() else '#2ecc71' for v in vals]
bars = ax.barh(range(len(labels)), vals, color=colors, alpha=0.8, height=0.6)
ax.axvline(x=df_minion['属性效率'].mean(), color='#f39c12', linestyle='--', linewidth=2,
           label=f'随从整体均值 ({df_minion["属性效率"].mean():.3f})')
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels, fontsize=10)
ax.set_xlabel('属性效率 (E)', fontsize=13)
ax.set_title('新机制关键词随从效率对比', fontsize=15, fontweight='bold')

for bar, val, n in zip(bars, vals, df_new_eff['数量'].values):
    ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
            f'{val:.3f} (n={n})', va='center', fontsize=9)

ax.legend(loc='best', fontsize=11)
plt.tight_layout()
plt.savefig(f'{OUTDIR}/chart10_new_mechanics_efficiency.png', dpi=150, bbox_inches='tight')
plt.close()
print("  图10: chart10_new_mechanics_efficiency.png 已保存")

# ============================================================
# 13. 保存分析数据供PDF使用
# ============================================================
import pickle

analysis_data = {
    'kw_dist': kw_dist,
    'eff_summary': df_eff_summary,
    'new_kw_detail': df_new_detail,
    'new_eff': df_new_eff,
    'total_cards': len(df),
    'total_minions': len(df_minion),
    'avg_eff_all': round(df['属性效率'].mean(), 3),
    'avg_eff_minion': round(df_minion['属性效率'].mean(), 3),
    'combo_top10': combo_counter.most_common(10),
    'set_kw_matrix': set_kw_matrix,
    'class_kw_matrix': class_kw_matrix,
}

with open(f'{OUTDIR}/analysis_data_v2.pkl', 'wb') as f:
    pickle.dump(analysis_data, f)

print("\n" + "=" * 60)
print("关键词分析完成！共生成 10 张图表")
print("=" * 60)
