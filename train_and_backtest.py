import sqlite3
import lightgbm as lgb
import numpy as np
import pandas as pd

# 1. 讀取特徵數據
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

# 2. 跨季切分 (2023-2025 訓練, 2025-2026 盲測 815 場)
train_df = df[df['race_date'] < '2025/09/01'].copy()
test_df = df[df['race_date'] >= '2025/09/01'].copy()

# 3. 訓練 LGBMRanker
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

# 4. 生成場內排序概率
test_df['rank_score'] = ranker.predict(test_df[features])
max_score = test_df.groupby('race_id')['rank_score'].transform('max')
test_df['exp_score'] = np.exp(test_df['rank_score'] - max_score)
sum_exp = test_df.groupby('race_id')['exp_score'].transform('sum')
test_df['model_prob'] = test_df['exp_score'] / sum_exp

# 5. 去抽水公平勝率與 Benter 對數融合 (70% 市場 + 30% Ranker)
test_df['inv_odds'] = 1.0 / test_df['win_odds'].replace(0, np.nan)
race_takeout = test_df.groupby('race_id')['inv_odds'].transform('sum')
test_df['fair_market_prob'] = test_df['inv_odds'] / race_takeout

p_mkt = test_df['fair_market_prob'].clip(lower=1e-5)
p_ml = test_df['model_prob'].clip(lower=1e-5)
test_df['log_score'] = 0.70 * np.log(p_mkt) + 0.30 * np.log(p_ml)

max_log = test_df.groupby('race_id')['log_score'].transform('max')
test_df['exp_log'] = np.exp(test_df['log_score'] - max_log)
sum_exp_log = test_df.groupby('race_id')['exp_log'].transform('sum')
test_df['final_prob'] = test_df['exp_log'] / sum_exp_log

# 6. 計算指標與場內排名
test_df['ev'] = (test_df['final_prob'] * test_df['win_odds']) - 1.0
test_df['edge'] = test_df['final_prob'] / test_df['fair_market_prob']
test_df['predicted_rank'] = (
    test_df.groupby('race_id')['final_prob']
    .rank(ascending=False, method='first')
    .astype(int)
)


# 7. 獨贏策略評估函數
def evaluate_win_strategy(
    min_edge, min_odds, max_odds, min_prob=0.20, kelly_frac=0.20
):
    candidates = test_df[
        (test_df['predicted_rank'] == 1)
        & (test_df['win_odds'] >= min_odds)
        & (test_df['win_odds'] <= max_odds)
        & (test_df['final_prob'] >= min_prob)
        & (test_df['edge'] >= min_edge)
    ].copy()

    if candidates.empty:
        return None

    candidates['full_kelly'] = np.maximum(
        0, candidates['ev'] / (candidates['win_odds'] - 1.0)
    )
    candidates['stake_pct'] = candidates['full_kelly'] * kelly_frac

    current_bankroll = 10000.0
    total_stake = 0.0
    total_payout = 0.0

    for _, bet in candidates.iterrows():
        # 若無 Kelly 正優勢則固定投注本金 1.5%
        stake = (
            current_bankroll * bet['stake_pct']
            if bet['stake_pct'] > 0
            else current_bankroll * 0.015
        )
        stake = min(stake, current_bankroll * 0.04)

        if stake < 10:
            stake = 10 if current_bankroll >= 10 else 0
        if stake == 0:
            continue

        total_stake += stake
        if bet['is_win'] == 1:
            payout = stake * bet['win_odds']
            current_bankroll += payout - stake
            total_payout += payout
        else:
            current_bankroll -= stake

    total_bets = len(candidates)
    wins = len(candidates[candidates['is_win'] == 1])
    win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
    roi = (
        ((total_payout - total_stake) / total_stake * 100)
        if total_stake > 0
        else 0.0
    )

    return {
        'min_edge': min_edge,
        'odds_range': f'{min_odds}-{max_odds}',
        'min_prob': min_prob,
        'bets': total_bets,
        'wins': wins,
        'win_rate': round(win_rate, 2),
        'total_stake': round(total_stake, 2),
        'roi': round(roi, 2),
        'profit': round(current_bankroll - 10000.0, 2),
        'final_bankroll': round(current_bankroll, 2),
    }


# ================= 輸出回測報告 =================
print('=' * 75)
print('   🎯 LGBMRanker【獨贏策略網格回測】(2025/2026 馬季 815 場盲測)')
print('=' * 75)

results = []
for edge_th in [0.95, 1.00, 1.05, 1.10]:
    for max_o in [3.0, 4.5, 6.0]:
        for min_p in [0.20, 0.25, 0.28]:
            res = evaluate_win_strategy(
                min_edge=edge_th,
                min_odds=1.5,
                max_odds=max_o,
                min_prob=min_p,
                kelly_frac=0.20,
            )
            if res and res['bets'] >= 10:
                results.append(res)

if results:
    res_df = pd.DataFrame(results).sort_values('roi', ascending=False)
    print(
        res_df[
            [
                'min_edge',
                'odds_range',
                'min_prob',
                'bets',
                'wins',
                'win_rate',
                'roi',
                'profit',
                'final_bankroll',
            ]
        ].to_string(index=False)
    )
else:
    print('⚠️ 無符合設定條件的策略組合。')

# 8. Top 1 馬匹位置（前三名 Place）基礎命中率統計
top1_all = test_df[test_df['predicted_rank'] == 1]
total_top1 = len(top1_all)
place_wins = len(top1_all[top1_all['is_place'] == 1])
place_rate = (place_wins / total_top1) * 100 if total_top1 > 0 else 0

top1_solid = test_df[
    (test_df['predicted_rank'] == 1) & (test_df['final_prob'] >= 0.25)
]
solid_total = len(top1_solid)
solid_place_wins = len(top1_solid[top1_solid['is_place'] == 1])
solid_place_rate = (
    (solid_place_wins / solid_total) * 100 if solid_total > 0 else 0
)

print('\n' + '=' * 75)
print('   🛡️ LGBMRanker Top 1 馬匹【位置 (前三名) 穩定度】統計')
print('=' * 75)
print(
    f'全季 Top 1 總場數         : {total_top1} 場 | 上名: {place_wins} 次 |'
    f' 位置率: {place_rate:.2f}%'
)
print(
    f'高勝率組 (勝率 >= 25%)    : {solid_total} 場 | 上名:'
    f' {solid_place_wins} 次 | 位置率: {solid_place_rate:.2f}%'
)
print('=' * 75)