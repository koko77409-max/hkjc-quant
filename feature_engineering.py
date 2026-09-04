import re
import sqlite3
import numpy as np
import pandas as pd


def parse_time_to_seconds(time_str: str) -> float:
    if not isinstance(time_str, str) or not time_str.strip():
        return np.nan
    try:
        cleaned = time_str.replace(':', '.')
        parts = cleaned.split('.')
        if len(parts) == 3:
            return (
                float(parts[0]) * 60.0
                + float(parts[1])
                + float(parts[2]) / 100.0
            )
        elif len(parts) == 2:
            return float(parts[0]) + float(parts[1]) / 100.0
        return float(cleaned)
    except Exception:
        return np.nan


def clean_rank(rank_str: str) -> int:
    if not isinstance(rank_str, str):
        return np.nan
    match = re.search(r'^\d+', rank_str.strip())
    return int(match.group(0)) if match else np.nan


# 1. 讀取數據
conn = sqlite3.connect('hkjc_racing.db')
df = pd.read_sql_query(
    'SELECT * FROM race_results ORDER BY race_date ASC, race_no ASC', conn
)

# 2. 清洗與時間差計算
df['rank_num'] = df['ranking'].apply(clean_rank)
df = df.dropna(subset=['rank_num']).copy()
df['rank_num'] = df['rank_num'].astype(int)
df['is_win'] = (df['rank_num'] == 1).astype(int)
df['is_place'] = (df['rank_num'] <= 3).astype(int)

# 定義排序學習相關性得分 (Rank Relevance)
df['relevance'] = 0
df.loc[df['rank_num'] == 1, 'relevance'] = 5
df.loc[df['rank_num'] == 2, 'relevance'] = 3
df.loc[df['rank_num'] == 3, 'relevance'] = 1

df['finish_seconds'] = df['finish_time'].apply(parse_time_to_seconds)
df['draw'] = pd.to_numeric(df['draw'], errors='coerce').fillna(7.0)
df['actual_weight'] = pd.to_numeric(
    df['actual_weight'], errors='coerce'
).fillna(120.0)
df['declared_weight'] = pd.to_numeric(
    df['declared_weight'], errors='coerce'
).fillna(1100.0)
df['win_odds'] = pd.to_numeric(df['win_odds'], errors='coerce').fillna(20.0)
df['race_date_dt'] = pd.to_datetime(df['race_date'])
df['race_id'] = df['race_date'] + '_' + df['race_no'].astype(str)

# 3. 每場時間標準化 (Z-score Normalized Time Behind)
winner_times = (
    df[df['is_win'] == 1]
    .groupby('race_id')['finish_seconds']
    .min()
    .rename('winner_time')
)
df = df.merge(winner_times, on='race_id', how='left')
df['winner_time'] = df['winner_time'].fillna(
    df.groupby('race_id')['finish_seconds'].transform('min')
)
df['time_behind'] = (df['finish_seconds'] - df['winner_time']).clip(
    lower=0.0, upper=10.0
)

# 馬匹近仗表現
df['horse_prev_tb'] = (
    df.groupby('horse_code')['time_behind'].shift(1).fillna(1.5)
)
df['horse_prev_rank'] = (
    df.groupby('horse_code')['rank_num'].shift(1).fillna(7.0)
)
df['horse_career_runs'] = df.groupby('horse_code').cumcount()

# 4. 騎練累積數據
df['jockey_cum_places'] = (
    df.groupby('jockey')['is_place'].cumsum() - df['is_place']
)
df['jockey_cum_runs'] = df.groupby('jockey').cumcount()
df['jockey_place_rate'] = (
    df['jockey_cum_places'] / df['jockey_cum_runs'].replace(0, np.nan)
).fillna(0.20)

df['trainer_cum_places'] = (
    df.groupby('trainer')['is_place'].cumsum() - df['is_place']
)
df['trainer_cum_runs'] = df.groupby('trainer').cumcount()
df['trainer_place_rate'] = (
    df['trainer_cum_places'] / df['trainer_cum_runs'].replace(0, np.nan)
).fillna(0.20)

# 5. 場內相對特徵 (In-Race Relative Features)
df['rel_weight'] = df['actual_weight'] - df.groupby('race_id')[
    'actual_weight'
].transform('mean')
df['rel_draw'] = df['draw'] - df.groupby('race_id')['draw'].transform('mean')
df['rel_jockey_rate'] = df['jockey_place_rate'] - df.groupby('race_id')[
    'jockey_place_rate'
].transform('mean')
df['rel_trainer_rate'] = df['trainer_place_rate'] - df.groupby('race_id')[
    'trainer_place_rate'
].transform('mean')
df['rel_prev_tb'] = df['horse_prev_tb'] - df.groupby('race_id')[
    'horse_prev_tb'
].transform('mean')

# 6. 存入資料庫
df.to_sql('model_features', conn, if_exists='replace', index=False)
conn.close()
print(f'✅ 特徵工程 2.0 完成！已構建場內相對特徵與 Relevance 標籤。')