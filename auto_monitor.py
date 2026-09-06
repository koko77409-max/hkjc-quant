# -*- coding: utf-8 -*-
import time
import datetime
from weather_service import WeatherService
from engine import update_and_push

print("=" * 60)
print("🏇 機構級 HKJC 自動監控與高頻狙擊系統 (Sniper Active)")
print("=" * 60)

weather = WeatherService()

while True:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 氣象感測
    try:
        w_info = weather.fetch_racecourse_weather()
        print(f"\n[{now_str}] 🍃 官方跑道環境感測: {w_info['summary']}")
    except Exception as e:
        print(f"\n[{now_str}] ⚠️ 氣象抓取略過: {e}")
    
    # 執行注單與網頁更新
    print(f"[{now_str}] 🚀 正在執行盤口掃描與發布儀表板...")
    try:
        update_and_push()
    except Exception as e:
        print(f"[{now_str}] ❌ 更新發布失敗: {e}")
    
    sleep_seconds = 120
    print(f"[{now_str}] 💤 進入休眠，{sleep_seconds} 秒後執行下一輪狙擊掃描...")
    time.sleep(sleep_seconds)
