# -*- coding: utf-8 -*-
import time
import subprocess
import datetime
from weather_service import WeatherService

print("=" * 60)
print("🏇 機構級 HKJC 自動監控與高頻狙擊系統 (Sniper Active)")
print("=" * 60)

weather = WeatherService()

def run_pipeline():
    subprocess.run(["python", "publish_dashboard.py"], check=False)

while True:
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 呼叫全新跑馬地/沙田官方環境微感測器
    w_info = weather.fetch_racecourse_weather()
    print(f"\n[{now_str}] 🍃 官方跑道環境感測: {w_info['summary']}")
    
    # 執行注單運算與發布更新
    print(f"[{now_str}] 🚀 正在執行盤口掃描與發布儀表板...")
    run_pipeline()
    
    sleep_seconds = 120
    print(f"[{now_str}] 💤 進入休眠，{sleep_seconds} 秒後執行下一輪狙擊掃描...")
    time.sleep(sleep_seconds)
