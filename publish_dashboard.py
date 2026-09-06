# -*- coding: utf-8 -*-
import os
import re
import datetime
import subprocess

print("🚀 [1/3] 正在執行盤口量化計算...")
subprocess.run(["python", "live_smart_betslip.py"], check=False)

html_path = os.path.abspath("public/index.html")
if not os.path.exists(html_path):
    print("❌ 找不到 public/index.html！")
    exit(1)

with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

print("🛠️ [2/3] 正在更新即時時間戳與儀表板...")
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

html = re.sub(r'\|\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+更新', f'| {now_str} 更新', html)
html = re.sub(r'更新時間：<strong[^>]*>[^<]+<\/strong>', f'更新時間：<strong style="color: #38bdf8;">{now_str}</strong>', html)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("🚀 [3/3] 正在同步至 GitHub Pages...")
subprocess.run(["git", "add", "public/index.html", "quant_core.py", "publish_dashboard.py", "auto_monitor.py"], check=False)

# 檢查是否有內容變更，避免無變更時 git commit 拋出異常崩潰
status_check = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
if status_check.stdout.strip():
    subprocess.run(["git", "commit", "-m", f"chore(auto): update quant betslip ({now_str})"], check=False)
    push_res = subprocess.run(["git", "push", "origin", "main"], check=False)
    if push_res.returncode == 0:
        print(f"🎉 [{now_str}] GitHub Pages 已同步更新完畢！")
    else:
        print(f"⚠️ [{now_str}] Git Push 暫時失敗，稍後輪詢將自動重試。")
else:
    print(f"ℹ️ [{now_str}] 內容無變動，略過本次提交。")
