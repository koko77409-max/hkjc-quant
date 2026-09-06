import sqlite3
import time
from bs4 import BeautifulSoup
import requests


def fetch_and_save_race_result(race_date_str, race_no, db_path='hkjc_racing.db'):
  """抓取單場已完賽賽果並寫入 SQLite"""
  url = f'https://racing.hkjc.com/racing/information/Chinese/racing/LocalResults.aspx?RaceDate={race_date_str}&RaceNo={race_no}'
  headers = {
      'User-Agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      )
  }

  res = requests.get(url, headers=headers, timeout=10)
  res.encoding = 'utf-8'
  soup = BeautifulSoup(res.text, 'html.parser')

  # 檢查賽事是否已出結果
  table = soup.find('table', {'class': 'tableBorder0'}) or soup.find(
      'table', {'class': 'draggable'}
  )
  if not table:
    return False

  conn = sqlite3.connect(db_path)
  cursor = conn.cursor()

  # 建立賽果儲存表
  cursor.execute("""
    CREATE TABLE IF NOT EXISTS race_results (
        race_date TEXT,
        race_no INTEGER,
        finishing_rank INTEGER,
        horse_no TEXT,
        horse_name TEXT,
        finish_time TEXT,
        win_odds REAL,
        PRIMARY KEY (race_date, race_no, horse_no)
    )
    """)

  rows = table.find_all('tr')
  has_data = False
  for r in rows:
    cols = [td.get_text(strip=True) for td in r.find_all('td')]
    # 正式賽果第一欄為名次（1, 2, 3...）
    if cols and cols[0].isdigit():
      rank = int(cols[0])
      h_no = cols[1]
      h_name = cols[2]
      finish_time = cols[10] if len(cols) > 10 else ''
      odds = float(cols[11]) if len(cols) > 11 and cols[11].replace('.', '').isdigit() else 0.0

      cursor.execute(
          """
            INSERT OR REPLACE INTO race_results 
            (race_date, race_no, finishing_rank, horse_no, horse_name, finish_time, win_odds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
          (race_date_str, race_no, rank, h_no, h_name, finish_time, odds),
      )
      has_data = True

  conn.commit()
  conn.close()
  return has_data