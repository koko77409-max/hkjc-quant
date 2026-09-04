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

# 2. 跨季盲測分割 (2023-2025 訓練 1,561 場，2025-2026 盲測 815 場)
train_df = df[df['race_date'] < '2025/09/01'].copy()
test_df = df[df['race_date'] >= '2025/09/01'].copy()

# 3. 訓練 LGBMRanker 排序學習模型
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

# 5. 在每場賽事內依模型勝率降序排名
test_df['model_rank'] = (
    test_df.groupby('race_id')['model_prob']
    .rank(ascending=False, method='first')
    .astype(int)
)

# 6. 回測統計：取出每場 Top 3 進行互串判定
total_races = test_df['race_id'].nunique()

q_hits = 0  # 連贏 (Q) 命中場數 (3 注中 1 注)
qp_race_hits = 0  # 位置 Q (QP) 有中獎的場數
qp_single_hits = 0  # 中 1 注 QP (3 隻中 2 隻在前三)
qp_triple_hits = 0  # 中齊 3 注 QP (3 隻全包前三名)
trio_hits = 0  # 單 T (Trio) 命中場數 (3 隻全包前三)
tierce_hits = 0  # 三重彩 (Tierce) 命中場數 (6 注中 1 注)

for rid, group in test_df.groupby('race_id'):
    top3 = group.sort_values('model_rank').head(3)
    actual_ranks = top3['rank_num'].tolist()

    # 前三名出現數量
    places_count = sum([1 for r in actual_ranks if r in [1, 2, 3]])

    # 1. 連贏 Q 判定 (冠亞軍 1 & 2 是否全在 Top 3 內)
    if 1 in actual_ranks and 2 in actual_ranks:
        q_hits += 1

    # 2. 位置 Q 判定
    if places_count == 2:
        qp_single_hits += 1
        qp_race_hits += 1
    elif places_count == 3:
        qp_triple_hits += 1  # 3 隻全包前三名 -> 中齊 3 注 QP！
        qp_race_hits += 1

    # 3. 單 T (Trio) 與 三重彩 (Tierce) 判定
    if set(actual_ranks) == {1, 2, 3}:
        trio_hits += 1
        tierce_hits += 1

# ================= 輸出回測統計報告 =================
print('=' * 75)
print('     🏆 2025/2026 全馬季「每場最高勝率 Top 3 馬匹互串」盲測報告')
print(f'     回測賽事總數 : {total_races} 場 (涵蓋沙田、跑馬地全季賽事)')
print('=' * 75)

print('\n【 1. 連贏互串 (Q Box - 每場 3 注) 】')
print(f'  • 總下注場數   : {total_races} 場 (總投注 {total_races * 3:,} 注)')
print(f'  • 命中 Q 場數  : {q_hits} 場')
print(f'  • 命中率 (Rate): {q_hits / total_races * 100:.2f}% (公眾隨機 ~3.5%)')
print(
    f'  • 平均命中頻率 : 每 {total_races / q_hits:.1f} 場中 1 次 Q'
    f' (每場成本 $30)'
)

print('\n' + '-' * 75)
print('【 2. 位置 Q 互串 (QP Box - 每場 3 注) 】')
print(f'  • 總下注場數   : {total_races} 場 (總投注 {total_races * 3:,} 注)')
print(
    f'  • 總中獎場數   : {qp_race_hits} 場 (命中率:'
    f' {qp_race_hits / total_races * 100:.2f}%)'
)
print(f'     ├ 中 1 注 QP: {qp_single_hits} 場')
print(
    f'     └ 💥中齊 3 注 QP: {qp_triple_hits} 場 (前三名全包，同時收 3'
    f' 份派彩！)'
)
print(f'  • 平均命中頻率 : 每 {total_races / qp_race_hits:.1f} 場中獎一次')

print('\n' + '-' * 75)
print('【 3. 單 T (Trio - 3 隻互串只需 1 注) 】')
print(f'  • 總下注場數   : {total_races} 場 (每場僅 $10，總投注 ${total_races * 10:,})')
print(f'  • 命中單 T 場數: {trio_hits} 場')
print(f'  • 命中率 (Rate): {trio_hits / total_races * 100:.2f}% (公眾隨機 ~0.3%)')
print(f'  • 說明         : 單 T 派彩通常 $150 至 $800，極具小博大槓桿')

print('\n' + '-' * 75)
print('【 4. 三重彩互串 (Tierce Box - 每場 6 注) 】')
print(f'  • 總下注場數   : {total_races} 場 (每場 $60，總投注 ${total_races * 60:,})')
print(f'  • 命中三重彩   : {tierce_hits} 場')
print(f'  • 命中率 (Rate): {tierce_hits / total_races * 100:.2f}%')
print(f'  • 說明         : 命中次數與單 T 相同，但成本需 6 注 ($60)')
print('=' * 75 + '\n')