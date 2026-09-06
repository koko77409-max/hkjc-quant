import sqlite3
import pandas as pd

# 讀取剛剛下載的數據
conn = sqlite3.connect('hkjc_racing.db')
df = pd.read_sql_query(
    'SELECT race_date, race_no, ranking, horse_name, horse_code, jockey, win_odds FROM race_results LIMIT 15',
    conn,
)
print(df)
conn.close()