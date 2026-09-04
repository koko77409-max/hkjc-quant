import sqlite3
import joblib
import numpy as np
import pandas as pd

# 1. 載入訓練好的模型
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


def predict_race_day(
    df_live_race: pd.DataFrame, bankroll: float = 10000.0
) -> pd.DataFrame:
    """傳入當日賽事排位及即時賠率 DataFrame，輸出符合 +EV 條件的推薦注碼"""
    df = df_live_race.copy()

    # 1. 計算去抽水市場公平勝率
    df['inv_odds'] = 1.0 / df['win_odds'].replace(0, np.nan)
    race_takeout = df.groupby('race_no')['inv_odds'].transform('sum')
    df['fair_market_prob'] = df['inv_odds'] / race_takeout

    # 2. 模型預測勝率
    df['raw_prob'] = model.predict_proba(df[features])[:, 1]
    df['model_prob'] = df.groupby('race_no', sort=False)['raw_prob'].transform(
        lambda x: x / x.sum() if x.sum() > 0 else x
    )

    # 3. 計算優勢比率 (Edge) 與期望值 (EV)
    df['edge'] = df['model_prob'] / df['fair_market_prob'].clip(lower=1e-4)
    df['ev'] = (df['model_prob'] * df['win_odds']) - 1.0

    # 4. 嚴格過濾經回測驗證的最佳盈利參數區間
    # 賠率 <= 5.5, Edge >= 1.15, 模型勝率 >= 18%
    candidates = df[
        (df['win_odds'] >= 2.0)
        & (df['win_odds'] <= 5.5)
        & (df['model_prob'] >= 0.18)
        & (df['edge'] >= 1.15)
    ].copy()

    if candidates.empty:
        print('⚠️ 今日無符合嚴格 +EV 門檻的推薦標的，建議觀望保持資金。')
        return pd.DataFrame()

    # 5. 計算 1/4 凱利注碼
    candidates['full_kelly'] = np.maximum(
        0, candidates['ev'] / (candidates['win_odds'] - 1.0)
    )
    candidates['stake_pct'] = candidates['full_kelly'] * 0.25

    # 每場選 1 匹 Edge 最大馬匹
    best_bets = (
        candidates.sort_values(['race_no', 'edge'], ascending=[True, False])
        .groupby('race_no')
        .first()
        .reset_index()
    )

    # 計算具體下注金額（最低 $10，單注上限 5% 本金）
    best_bets['bet_amount'] = (bankroll * best_bets['stake_pct']).clip(
        lower=10, upper=bankroll * 0.05
    )
    best_bets['bet_amount'] = (best_bets['bet_amount'] // 10) * 10  # 取整至 $10

    output_cols = [
        'race_no',
        'horse_no',
        'horse_name',
        'win_odds',
        'model_prob',
        'fair_market_prob',
        'edge',
        'ev',
        'bet_amount',
    ]

    return best_bets[output_cols].sort_values('race_no')