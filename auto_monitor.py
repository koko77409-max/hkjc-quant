import time
import subprocess
import datetime

INTERVAL = 180  # 3 分鐘輪詢一次

print("=" * 60)
print("🏇 香港賽馬量化即時監控系統 (Daemon Mode)")
print(f"⏱️ 輪詢週期: 每 {INTERVAL} 秒自動掃描盤口並推送至 GitHub Pages")
print("=" * 60)

while True:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now_str}] 開始掃描盤口與更新注單...")
    try:
        # 直接調用剛才驗證成功的 publish_dashboard.py
        res = subprocess.run(["python", "publish_dashboard.py"], check=False)
        if res.returncode == 0:
            print(f"[{now_str}] ✅ 儀表板已順利更新並推送至 GitHub Pages！")
        else:
            print(f"[{now_str}] ⚠️ 發布過程回傳狀態碼: {res.returncode}")
    except Exception as e:
        print(f"[{now_str}] ❌ 執行異常: {e}")

    print(f"進入休眠，{INTERVAL} 秒後自動進行下次掃描... (請勿關閉視窗)")
    time.sleep(INTERVAL)
