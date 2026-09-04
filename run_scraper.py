import io
import re
import sqlite3
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 1. 初始化資料庫
conn = sqlite3.connect('hkjc_racing.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS race_results (
    race_date TEXT,
    race_no INTEGER,
    ranking TEXT,
    horse_no TEXT,
    horse_name TEXT,
    horse_code TEXT,
    jockey TEXT,
    trainer TEXT,
    actual_weight TEXT,
    declared_weight TEXT,
    draw TEXT,
    finish_time TEXT,
    win_odds REAL,
    PRIMARY KEY (race_date, race_no, horse_code)
)
""")
conn.commit()

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,'
        ' like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
}


def fetch_and_save_race(race_date: str, race_no: int):
    url = f'https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate={race_date}&RaceNo={race_no}'

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'

        if (
            res.status_code != 200
            or '沒有相關賽事資料' in res.text
            or '賽事重溫' not in res.text
        ):
            print(f'❌ {race_date} 第 {race_no} 場：無賽事資料或頁面未就緒')
            return False

        # 使用 read_html 自動解析所有表格
        dfs = pd.read_html(io.StringIO(res.text))

        target_df = None
        for df in dfs:
            # 尋找包含「名次」與「馬名」的主賽果表格
            cols_str = ''.join([str(c) for c in df.columns])
            if '名次' in cols_str and '馬名' in cols_str:
                target_df = df
                break

        if target_df is None or target_df.empty:
            print(f'⚠️ {race_date} 第 {race_no} 場：未能定位賽果表格')
            return False

        records = []
        for _, row in target_df.iterrows():
            ranking = str(row.iloc[0]).strip()
            # 略過非馬匹列（如退出的馬匹備註或表尾文字）
            if not ranking or ranking == 'nan':
                continue

            horse_no = str(row.iloc[1]).strip()
            raw_horse = str(row.iloc[2]).strip()

            # 提取馬名與括號內的烙號（例如：金鑽貴人(G180)）
            match = re.search(r'^(.*?)\((.*?)\)', raw_horse)
            if match:
                horse_name = match.group(1).strip()
                horse_code = match.group(2).strip()
            else:
                horse_name = raw_horse
                horse_code = horse_name  # 無烙號時以馬名作備用

            jockey = str(row.iloc[3]).strip() if len(row) > 3 else ''
            trainer = str(row.iloc[4]).strip() if len(row) > 4 else ''
            actual_weight = str(row.iloc[5]).strip() if len(row) > 5 else ''
            declared_weight = str(row.iloc[6]).strip() if len(row) > 6 else ''
            draw = str(row.iloc[7]).strip() if len(row) > 7 else ''
            finish_time = str(row.iloc[10]).strip() if len(row) > 10 else ''

            try:
                win_odds = float(str(row.iloc[11]).replace(',', '').strip())
            except (ValueError, IndexError):
                win_odds = None

            records.append((
                race_date,
                race_no,
                ranking,
                horse_no,
                horse_name,
                horse_code,
                jockey,
                trainer,
                actual_weight,
                declared_weight,
                draw,
                finish_time,
                win_odds,
            ))

        if records:
            cursor.executemany(
                """
                INSERT OR REPLACE INTO race_results 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                records,
            )
            conn.commit()
            print(
                f'✅ 成功儲存：{race_date} 第 {race_no} 場（共 {len(records)} 匹馬）'
            )
            return True
        else:
            print(f'⚠️ {race_date} 第 {race_no} 場：未解析到馬匹數據')
            return False

    except Exception as e:
        print(f'❌ {race_date} 第 {race_no} 場發生錯誤：{e}')
        return False


# 執行抓取測試（以 2024/07/14 煞科日為例）
target_date = '2024/07/14'
print(f'=== 開始抓取 {target_date} 賽事數據 ===')

for r_no in range(1, 12):
    success = fetch_and_save_race(target_date, r_no)
    if not success:
        # 連續失敗可能已超出當日場數
        break
    time.sleep(1.5)

conn.close()
print('=== 抓取程序完畢 ===')