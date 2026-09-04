from datetime import datetime, timedelta
import io
import re
import sqlite3
import time
import pandas as pd
import requests

# 1. 連接或建立 SQLite 資料庫
conn = sqlite3.connect('hkjc_racing.db')
cursor = conn.cursor()

# 確保賽果資料表存在
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


def is_already_scraped(race_date: str, race_no: int) -> bool:
    """檢查該場次是否已存在於資料庫中"""
    cursor.execute(
        'SELECT 1 FROM race_results WHERE race_date = ? AND race_no = ? LIMIT'
        ' 1',
        (race_date, race_no),
    )
    return cursor.fetchone() is not None


def fetch_and_save_race(race_date: str, race_no: int) -> bool:
    """抓取單場賽事賽果並儲存至資料庫"""
    if is_already_scraped(race_date, race_no):
        print(f'⏭️ {race_date} 第 {race_no} 場已存在，跳過。')
        return True

    url = f'https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate={race_date}&RaceNo={race_no}'

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'

        if (
            res.status_code != 200
            or '沒有相關賽事資料' in res.text
            or '賽事重溫' not in res.text
        ):
            return False

        dfs = pd.read_html(io.StringIO(res.text))
        target_df = None
        for df in dfs:
            cols_str = ''.join([str(c) for c in df.columns])
            if '名次' in cols_str and '馬名' in cols_str:
                target_df = df
                break

        if target_df is None or target_df.empty:
            return False

        records = []
        for _, row in target_df.iterrows():
            ranking = str(row.iloc[0]).strip()
            if not ranking or ranking == 'nan':
                continue

            horse_no = str(row.iloc[1]).strip()
            raw_horse = str(row.iloc[2]).strip()

            match = re.search(r'^(.*?)\((.*?)\)', raw_horse)
            if match:
                horse_name = match.group(1).strip()
                horse_code = match.group(2).strip()
            else:
                horse_name = raw_horse
                horse_code = horse_name

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
        return False

    except Exception as e:
        print(f'❌ {race_date} 第 {race_no} 場抓取異常：{e}')
        return False


def run_batch_crawler(start_date_str: str, end_date_str: str):
    """遍歷區間內逢週三、六、日的賽事日進行自動抓取"""
    start_date = datetime.strptime(start_date_str, '%Y/%m/%d')
    end_date = datetime.strptime(end_date_str, '%Y/%m/%d')
    curr = start_date

    while curr <= end_date:
        # 0=週一, 2=週三, 5=週六, 6=週日 (香港主流賽事日)
        if curr.weekday() in [2, 5, 6]:
            date_str = curr.strftime('%Y/%m/%d')
            has_race_on_date = False

            for r_no in range(1, 12):
                success = fetch_and_save_race(date_str, r_no)
                if success:
                    has_race_on_date = True
                    time.sleep(1.0)
                else:
                    if r_no == 1:
                        # 第 1 場即無資料代表當天非賽馬日
                        break
                    # 已超出當天總場數
                    break

            if has_race_on_date:
                print(f'--- {date_str} 賽日處理完畢 ---')

        curr += timedelta(days=1)


if __name__ == '__main__':
    # 涵蓋近 3 個馬季（2023/24、2024/25、2025/26）
    season_start = '2023/09/01'
    season_end = '2026/07/15'

    print(
        f'=== 開始批量下載香港賽馬歷史數據 ({season_start} 至 {season_end}) ==='
    )
    run_batch_crawler(season_start, season_end)
    conn.close()
    print('🎉 批量下載完成！資料已完整更新至 2026 年 7 月。')