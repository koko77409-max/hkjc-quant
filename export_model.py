import sqlite3
import joblib
import lightgbm as lgb
import pandas as pd

# 1. 讀取全量特徵數據
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

# 2. 構建全量 Group 結構
groups = df.groupby('race_id', sort=False).size().values

# 3. 訓練全量 LGBMRanker (12 個特徵)
final_ranker = lgb.LGBMRanker(
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

final_ranker.fit(df[features], df['relevance'], group=groups)

# 4. 覆蓋導出模型檔案
joblib.dump(final_ranker, 'hkjc_model.pkl')
print(f'✅ 全量 12 特徵 LGBMRanker 模型已成功導出至 hkjc_model.pkl（樣本數：{len(df):,}）')