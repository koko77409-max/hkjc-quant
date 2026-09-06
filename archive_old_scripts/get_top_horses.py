import sqlite3
import joblib
import numpy as np
import pandas as pd

# 1. 載入訓練好的模型與特徵清單
model = joblib.load('hkjc_model.pkl')

features = [
    'horse_prev_time_behind',
    'horse_recent_avg_time_behind',
    'horse_recent_avg_rank',
    'jt_combo_win_rate',
    'jockey_place_rate',
    'trainer_place_rate',
    'draw',
    'actual_weight',
    'declared_weight',
    'weight_change',
    'rest_days',
    'horse_prev_odds',
    'horse_career_runs',
]

# 2. 讀取資料庫最新賽事特徵數據
conn = sqlite3.connect('hkjc_racing.db')
df = pd.read_sql_query(
    'SELECT * FROM model_features ORDER BY race_date ASC, race_no ASC', conn
)
conn.close()

# 3. 模型預測並計算場內正規化勝率
df['raw_prob'] = model.predict_proba(df[features])[:, 1]
df['model_prob'] = df.groupby('race_id', sort=False)['raw_prob'].transform(
    lambda x: x / x.sum() if x.sum() > 0 else x
)

# 4. 計算市場隱含勝率與期望值 (EV)
df['implied_prob'] = 1.0 / df['win_odds'].replace(0, np.nan)
df['ev'] = (df['model_prob'] * df['win_odds']) - 1.0

# 5. 在每場賽事內按「模型勝率」降序排名
df['model_rank'] = (
    df.groupby('race_id')['model_prob']
    .rank(ascending=False, method='first')
    .astype(int)
)

# 6. 取出最近一個賽馬日的所有場次進行展示
latest_date = df['race_date'].max()
recent_race_df = df[df['race_date'] == latest_date].copy()

print('=' * 65)
print(f'          🏇 {latest_date} 各場賽事「最大機會贏」焦點馬 (Top 1)')
print('=' * 65)

# 提取每場勝率最高的第 1 匹馬
top1_horses = (
    recent_race_df[recent_race_df['model_rank'] == 1]
    .sort_values('race_no')
    .copy()
)

for _, r in top1_horses.iterrows():
    p_pct = r['model_prob'] * 100
    mkt_pct = r['implied_prob'] * 100
    ev_pct = r['ev'] * 100
    ev_tag = '✅ (+EV)' if r['ev'] > 0 else '⚠️ (-EV)'

    print(f"第 {r['race_no']:2d} 場 | {r['horse_no']:2s} 號 {r['horse_name']}")
    print(
        f"   └ 預估勝率: {p_pct:5.1f}% | 當前賠率: {r['win_odds']:4.1f} 倍 |"
        f' 市場隱含: {mkt_pct:4.1f}% | 期望回報: {ev_pct:+5.1f}% {ev_tag}'
    )

print('\n' + '=' * 65)
print(f'       📋 {latest_date} 每場前 4 名最高勝率排行榜 (Top 4 Rankings)')
print('=' * 65)

top4_horses = recent_race_df[recent_race_df['model_rank'] <= 4].sort_values(
    ['race_no', 'model_rank']
)

for race_no, group in top4_horses.groupby('race_no'):
    print(f'\n【 第 {race_no} 場 】')
    disp_cols = group[
        ['model_rank', 'horse_no', 'horse_name', 'win_odds', 'model_prob']
    ].copy()
    disp_cols['model_prob'] = (disp_cols['model_prob'] * 100).map('{:.1f}%'.format)
    disp_cols.columns = ['預測名次', '馬號', '馬名', '賠率', '模型勝率']
    print(disp_cols.to_string(index=False))