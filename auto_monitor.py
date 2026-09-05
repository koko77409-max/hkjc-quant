import time
import datetime
import traceback
import subprocess
import os
import sys

# 確保環境變數使用 UTF-8，不篡改底層 file handle
os.environ["PYTHONIOENCODING"] = "utf-8"

import live_smart_betslip

def safe_git_push():
    try:
        subprocess.run(["git", "add", "public/index.html"], check=False, timeout=15)
        subprocess.run(["git", "commit", "-m", "auto: update live odds and exotics"], check=False, timeout=15)
        res = subprocess.run(["git", "push", "origin", "main"], check=False, timeout=30)
        if res.returncode == 0:
            print("[GIT] GitHub Pages 已成功同步最新預測！")
        else:
            print("[GIT] 推送將於下個週期重試。")
    except Exception as e:
        print(f"[GIT] 連線略過: {e}")

def main_loop():
    print("=" * 60)
    print("HKJC 自動輪詢監控守護進程已啟動！")
    print("輪詢週期: 每 3 分鐘 (180 秒) 自動重算並推送")
    print("=" * 60)

    while True:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n>>> [{now_str}] 觸發全量排位與賠率掃描...")

        try:
            # 執行完整量化運算、大彩池與 HTML 產生
            live_smart_betslip.run_smart_betslip()
            print(f"[{now_str}] 運算完成，準備推送至 GitHub Pages...")
            safe_git_push()
        except Exception as e:
            print(f"輪詢中發生異常 (守護進程保持存活): {e}")
            traceback.print_exc()

        print("進入休眠，180 秒後自動進行下次掃描... (請勿關閉視窗)")
        time.sleep(180)

if __name__ == "__main__":
    main_loop()
