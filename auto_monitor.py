from datetime import datetime, timedelta
import io
import os
import sys
import time
from live_smart_betslip import fetch_race_data, run_smart_betslip

# 目標賽事日期 (預設監控下一個賽馬日，如 2026/09/06 開鑼日)
TARGET_DATE = "2026/09/06"
CHECK_INTERVAL_SECONDS = 1200  # 每 20 分鐘檢查一次


def is_racecard_published(target_date: str) -> bool:
    """檢查馬會是否已上載第 1 場排位表"""
    df = fetch_race_data(target_date, 1)
    return not df.empty and len(df) >= 4


def generate_and_save_report(target_date: str):
    """執行策略計算並將終端機輸出同步寫入文字檔"""
    clean_date_str = target_date.replace("/", "")
    timestamp = datetime.now().strftime("%H%M")
    filename = f"betslip_{clean_date_str}_{timestamp}.txt"

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在生成量化投注單...")

    # 捕捉終端機 stdout 輸出
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()

    try:
        run_smart_betslip(target_date=target_date, bankroll=10000.0)
    finally:
        output_content = buffer.getvalue()
        sys.stdout = old_stdout

    # 同步印在終端機並存入 txt 檔案
    print(output_content)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"✅ 報告已成功儲存至: {os.path.abspath(filename)}")
    # 發出 Windows 系統提示音 (嗶聲)
    sys.stdout.write("\a\a\a")


def main():
    print("=" * 65)
    print(f"   🏇 香港賽馬排位自動監控系統啟動")
    print(f"   監控目標賽日 : {TARGET_DATE}")
    print(
        f"   輪詢頻率     : 每 {CHECK_INTERVAL_SECONDS // 60} 分鐘自動檢查一次"
    )
    print("=" * 65)

    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] 正在檢查馬會網頁是否已發布排位...")

        if is_racecard_published(TARGET_DATE):
            print(f"\n🎉 偵測到【 {TARGET_DATE} 】排位已正式發布！立即執行量化分析...")
            generate_and_save_report(TARGET_DATE)
            print("\n任務完成，監控腳本正常結束。")
            break
        else:
            print(
                f"⏳ 尚未公布排位。將於 {CHECK_INTERVAL_SECONDS // 60} 分鐘後重試...\n"
            )
            time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()