import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from live_smart_betslip import DB_PATH, fetch_race_data, get_upcoming_local_race
import pandas as pd
import sqlite3

def init_odds_table():
    """初始化賠率歷史流水表"""
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
        time.sleep(0.15)

    if records:
        conn.executemany(
            """
        INSERT INTO odds_history (race_date, race_no, horse_no, horse_name, win_odds, record_time)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
            records,
        )
        conn.commit()
        print(f'[{hkt_now}] 成功記錄 {target_date} 共 {len(records)} 筆即時賠率。')
    else:
        print(f'[{hkt_now}] 彩池尚未開售或未有有效賠率。')

    conn.close()
    return len(records)

def get_odds_movement_summary(target_date: str) -> pd.DataFrame:
    """計算初盤、最新賠率與大戶落飛跌幅"""
    conn = sqlite3.connect(DB_PATH)
    query = f"""
    SELECT race_no, horse_no, horse_name, win_odds, record_time
    FROM odds_history
    WHERE race_date = '{target_date}'
    ORDER BY record_time ASC
    """
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame()

    summary = []
    for (r_no, h_no), group in df.groupby(['race_no', 'horse_no']):
        open_odds = group.iloc[0]['win_odds']
        current_odds = group.iloc[-1]['win_odds']
        h_name = group.iloc[-1]['horse_name']

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

def run_pipeline():
    """本地更新網頁並自動推送至 GitHub"""
    print('🔄 正在重新生成 HTML 網頁...')
    subprocess.run(['python', 'generate_html.py'], check=True)

    print('🚀 自動同步至 GitHub Pages...')
    commands = [
        ['git', 'add', 'public/index.html', 'hkjc_racing.db'],
        ['git', 'commit', '-m', f'chore: live sync odds & betslip ({datetime.now().strftime("%H:%M:%S")})'],
        ['git', 'push', 'origin', 'main']
    ]
    for cmd in commands:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('✅ 本地同步完成，手機頁面已更新！\n')

def main_loop(interval_minutes: int = 3):
    """主循環常駐監控"""
    init_odds_table()
    target_date, venue_code = get_upcoming_local_race()
    venue_name = '沙田 (ST)' if venue_code == 'ST' else '跑馬地 (HV)'
    print('====================================================')
    print(f'🏇 HKJC 本地常駐賠率監控已啟動！')
    print(f'🎯 監控賽事: {target_date} {venue_name}')
    print(f'⏱️ 輪詢間隔: 每 {interval_minutes} 分鐘自動檢查一次')
    print('====================================================\n')

    while True:
        try:
            hkt_now = datetime.now(timezone(timedelta(hours=8)))
            print(f'>>> [{hkt_now.strftime("%H:%M:%S")}] 執行盤口掃描...')
            n_records = scan_and_record_odds(target_date, venue_code)

            if n_records > 0:
                run_pipeline()
            else:
                print('暫無賠率變動，稍後再試。')

        except Exception as e:
            print(f'⚠️ 執行過程發生異常: {e}')

        print(f'💤 等待 {interval_minutes} 分鐘後進行下次掃描... (按 Ctrl+C 可停止)\n')
        time.sleep(interval_minutes * 60)

if __name__ == '__main__':
    main_loop(interval_minutes=3)