import sqlite3
import lightgbm as lgb
import numpy as np
import pandas as pd

# 1. 讀取資料庫特徵
conn = sqlite3.connect('hkjc_racing.db')
df = pd.read_sql_query(
    'SELECT * FROM model_features ORDER BY race_date ASC, race_no ASC', conn
)
conn.close()

features = [
    'rel_weight',
    'rel_draw',
    'rel_jockey_rate',
    'rel_trainer_rate',
    'rel_prev_tb',
    'horse_prev_tb',
    'horse_prev_rank',
    'jockey_place_rate',
    'trainer_place_rate',
    'draw',
    'actual_weight',
    'horse_career_runs',
]

# 2. 嚴格跨季劃分 (2023-2025 訓練 1,561 場，2025-2026 盲測 815 場)
train_df = df[df['race_date'] < '2025/09/01'].copy()
test_df = df[df['race_date'] >= '2025/09/01'].copy()

# 3. 訓練 LGBMRanker 排序模型
train_groups = train_df.groupby('race_id', sort=False).size().values
ranker = lgb.LGBMRanker(
    objective='lambdarank',
    n_estimators=150,
    learning_rate=0.03,
    num_leaves=15,
    min_child_samples=30,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbose=-1,
)
ranker.fit(train_df[features], train_df['relevance'], group=train_groups)

# 4. 生成純模型場內排序分數與勝率
test_df['rank_score'] = ranker.predict(test_df[features])
max_score = test_df.groupby('race_id')['rank_score'].transform('max')
test_df['exp_score'] = np.exp(test_df['rank_score'] - max_score)
sum_exp = test_df.groupby('race_id')['exp_score'].transform('sum')
test_df['model_prob'] = test_df['exp_score'] / sum_exp

# 5. 取出每場純勝率最高（Top 1）馬匹
test_df['model_rank'] = (
    test_df.groupby('race_id')['model_prob']
    .rank(ascending=False, method='first')
    .astype(int)
)
top1_df = test_df[test_df['model_rank'] == 1].copy()

# 6. 計算位置 (Place) 估算派彩賠率
top1_df['est_place_odds'] = np.maximum(
    1.05, 1.0 + (top1_df['win_odds'] - 1.0) * 0.28
)

# ================= 策略 A：每日精選最強 2 匹穩膽 2 串 1 =================
stake_per_bet = 100.0  # 每注本金 $100

raceday_groups = top1_df.groupby('race_date')
stratA_bets = 0
stratA_hits = 0
stratA_total_stake = 0.0
stratA_total_payout = 0.0

for r_date, group in raceday_groups:
    if len(group) < 2:
        continue

    # 按模型勝率由大至小排序，取全日最高 2 匹馬
    top2_horses = group.sort_values('model_prob', ascending=False).iloc[0:2]
    leg1 = top2_horses.iloc[0]
    leg2 = top2_horses.iloc[1]

    stratA_bets += 1
    stratA_total_stake += stake_per_bet

    # 兩關皆跑入前三名 (位置) 方為中獎
    if leg1['is_place'] == 1 and leg2['is_place'] == 1:
        allup_odds = leg1['est_place_odds'] * leg2['est_place_odds']
        payout = stake_per_bet * allup_odds
        stratA_total_payout += payout
        stratA_hits += 1

stratA_profit = stratA_total_payout - stratA_total_stake
stratA_roi = (
    (stratA_profit / stratA_total_stake * 100) if stratA_total_stake > 0 else 0
)
stratA_win_rate = (stratA_hits / stratA_bets * 100) if stratA_bets > 0 else 0

# ================= 策略 B：高勝率門檻 (勝率 >= 28%) 穩膽 2 串 1 =================
stratB_bets = 0
stratB_hits = 0
stratB_total_stake = 0.0
stratB_total_payout = 0.0

for r_date, group in raceday_groups:
    solid_horses = group[group['model_prob'] >= 0.28].sort_values(
        'model_prob', ascending=False
    )
    if len(solid_horses) < 2:
        continue

    # 當日有 2 匹或以上勝率破 28% 時下注最強 2 匹
    leg1 = solid_horses.iloc[0]
    leg2 = solid_horses.iloc[1]

    stratB_bets += 1
    stratB_total_stake += stake_per_bet

    if leg1['is_place'] == 1 and leg2['is_place'] == 1:
        allup_odds = leg1['est_place_odds'] * leg2['est_place_odds']
        payout = stake_per_bet * allup_odds
        stratB_total_payout += payout
        stratB_hits += 1

stratB_profit = stratB_total_payout - stratB_total_stake
stratB_roi = (
    (stratB_profit / stratB_total_stake * 100) if stratB_total_stake > 0 else 0
)
stratB_win_rate = (stratB_hits / stratB_bets * 100) if stratB_bets > 0 else 0

# ================= 輸出回測報告 =================
print('=' * 75)
print('     🚀 2025/2026 全馬季「位置 2 串 1 (Place All-up)」跨季盲測報告')
print(f'     涵蓋賽事總數 : {len(top1_df)} 場 | 賽馬日總數 : {len(raceday_groups)} 日')
print('=' * 75)

print('\n【 策略 A：每個賽事日挑選「全日最強 2 匹」買 1 注 2 串 1 (每注 $100) 】')
print(f'  • 總下注賽日數 : {stratA_bets} 日 (總注數 {stratA_bets} 注)')
print(f'  • 成功過關次數 : {stratA_hits} 次')
print(
    f'  • 2 串 1 命中率 : {stratA_win_rate:.2f}% (公眾隨機 2 串 1 命中率約 5-8%)'
)
print(f'  • 總投注成本   : ${stratA_total_stake:,.0f}')
print(f'  • 總回收派彩   : ${stratA_total_payout:,.2f}')
print(f'  • 淨盈虧 (P/L) : ${stratA_profit:+,.2f}')
print(f'  • 投資回報率   : {stratA_roi:+.2f}%')

print('\n' + '-' * 75)
print(
    '【 策略 B：高確定性過關（僅當日有 2 匹或以上勝率 >= 28% 時下注，每注 $100） 】'
)
print(f'  • 符合條件賽日 : {stratB_bets} 日 (嚴格過濾無把握賽日)')
print(f'  • 成功過關次數 : {stratB_hits} 次')
print(f'  • 2 串 1 命中率 : {stratB_win_rate:.2f}%')
print(f'  • 總投注成本   : ${stratB_total_stake:,.0f}')
print(f'  • 總回收派彩   : ${stratB_total_payout:,.2f}')
print(f'  • 淨盈虧 (P/L) : ${stratB_profit:+,.2f}')
print(f'  • 投資回報率   : {stratB_roi:+.2f}%')
print('=' * 75 + '\n')