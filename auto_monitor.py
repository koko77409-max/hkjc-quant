# -*- coding: utf-8 -*-
import time
import subprocess
import datetime
import os
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
    
    # 檢查即時風向
    w_info = weather.get_shatin_wind_bias()
    print(f"\n[{now_str}] 🍃 沙田即時氣象風力: {w_info['desc']}")
    
    # 執行注單運算與同步發布
    print(f"[{now_str}] 🚀 正在執行盤口掃描與發布...")
    run_pipeline()
    
    # 動態調整輪詢休眠：
    # 假設常規每 180 秒輪詢，若進入賽事開跑關鍵時段可設定為 15 秒高頻
    # 這裡預設為平穩 120 秒監控，確保不觸發 GitHub 頻率限制
    sleep_seconds = 120
    print(f"[{now_str}] 💤 進入休眠，{sleep_seconds} 秒後執行下一輪狙擊掃描...")
    time.sleep(sleep_seconds)
