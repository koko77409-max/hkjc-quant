import sqlite3
import joblib
import pandas as pd

# 1. 檢查資料庫
conn = sqlite3.connect('hkjc_racing.db')
df_res = pd.read_sql_query('SELECT * FROM race_results', conn)
df_feat = pd.read_sql_query('SELECT * FROM model_features', conn)
conn.close()

print('=' * 50)
print('        📊 賽馬量化系統就緒狀態檢查')
print('=' * 50)
print(f'歷史出賽紀錄總數 : {len(df_res):,} 條')
print(f'特徵庫樣本總數   : {len(df_feat):,} 條')
print(
    f'涵蓋賽事日期區間 : {df_res["race_date"].min()} 至'
    f' {df_res["race_date"].max()}'
)
print(f'獨立賽事總場數   : {len(df_res[["race_date", "race_no"]].drop_duplicates()):,} 場')
print(f'涵蓋現役/退役馬匹: {df_res["horse_code"].nunique():,} 匹')

# 2. 檢查模型檔案
try:
    model = joblib.load('hkjc_model.pkl')
    print('\n✅ 模型檔案 hkjc_model.pkl 加載成功！')
    print(f'模型特徵數量     : {model.n_features_in_} 個特徵')
    print('狀態評定         : 🟢 系統已全面就緒，可迎戰 2026/27 新馬季')
except Exception as e:
    print(f'\n❌ 模型檢查失敗: {e}')
print('=' * 50)