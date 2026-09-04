from datetime import datetime, timezone, timedelta
import sqlite3
import time
from live_smart_betslip import DB_PATH, fetch_race_data, get_upcoming_local_race
import pandas as pd


def init_odds_table():
    """初始化賠率歷史流水表記錄庫"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS odds_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_date TEXT,
        race_no INTEGER,
        horse_no TEXT,
        horse_name TEXT,
        win_odds REAL,
        record_time TEXT
    )
    """)
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_odds_time ON odds_history(race_date,'
        ' race_no, horse_no, record_time)'
    )
    conn.commit()
    conn.close()


def scan_and_record_odds(target_date: str, venue_code: str) -> int:
    """掃描當前全場賠率並寫入資料庫"""
    hkt_now = datetime.now(timezone(timedelta(hours=8))).strftime(
        '%Y-%m-%d %H:%M:%S'
    )
    conn = sqlite3.connect(DB_PATH)

    records = []
    for r_no in range(1, 12):
        df_race = fetch_race_data(target_date, r_no, venue_code)
        if df_race.empty:
            break

        valid_odds = df_race[
            df_race['win_odds'].notnull() & (df_race['win_odds'] > 1.0)
        ]
        for _, row in valid_odds.iterrows():
            records.append((
                target_date,
                int(r_no),
                str(row['horse_no']),
                str(row['horse_name']),
                float(row['win_odds']),
                hkt_now,
            ))
        time.sleep(0.2)

    if records:
        conn.executemany(
            """
        INSERT INTO odds_history (race_date, race_no, horse_no, horse_name, win_odds, record_time)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
            records,
        )
        conn.commit()
        print(
            f'[{hkt_now}] 成功記錄 {target_date} 共 {len(records)} 筆即時賠率。'
        )
    else:
        print(f'[{hkt_now}] 馬會尚未開售彩池，未有有效賠率。')

    conn.close()
    return len(records)


def get_odds_movement_summary(target_date: str) -> pd.DataFrame:
    """計算各匹馬的初盤開售賠率、最新賠率與大戶落飛跌幅"""
    conn = sqlite3.connect(DB_PATH)
    query = f"""
    SELECT race_no, horse_no, horse_name, win_odds, record_time
    FROM odds_history
    WHERE race_date = '{target_date}'
    ORDER BY record_time ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    summary = []
    for (r_no, h_no), group in df.groupby(['race_no', 'horse_no']):
        open_odds = group.iloc[0]['win_odds']
        current_odds = group.iloc[-1]['win_odds']
        h_name = group.iloc[-1]['horse_name']

        # 計算跌幅：若 10.0 跌至 5.0， drop_pct = (10 - 5) / 10 = +50% (正數代表落飛，負數代表冷卻回升)
        drop_pct = (
            ((open_odds - current_odds) / open_odds) * 100.0
            if open_odds > 0
            else 0.0
        )

        summary.append({
            'race_no': int(r_no),
            'horse_no': str(h_no),
            'horse_name': h_name,
            'open_odds': open_odds,
            'current_odds': current_odds,
            'drop_pct': drop_pct,
            'records_count': len(group),
        })

    return pd.DataFrame(summary)


if __name__ == '__main__':
    init_odds_table()
    target_date, venue_code = get_upcoming_local_race()
    print(f'🚀 啟動即時賠率記錄，目標賽事：{target_date} ({venue_code})')
    scan_and_record_odds(target_date, venue_code)