# -*- coding: utf-8 -*-
import os, re, datetime, subprocess

print("🚀 [1/3] 正在執行盤口量化計算...")
subprocess.run(["python", "live_smart_betslip.py"], check=False)

html_path = os.path.abspath("public/index.html")
with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

print("🛠️ [2/3] 正在更新 1 膽拖 4 腳單 T 策略...")
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

html = re.sub(r'\|\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+更新', f'| {now_str} 更新', html)
html = re.sub(r'更新時間：<strong[^>]*>[^<]+<\/strong>', f'更新時間：<strong style="color: #38bdf8;">{now_str}</strong>', html)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("🚀 [3/3] 正在推送到 GitHub Pages...")
subprocess.run(["git", "add", "public/index.html", "publish_dashboard.py"], check=True)
subprocess.run(["git", "commit", "-m", f"feat(trio): upgrade Strategy 2 to 1 Banker 4 Legs ({now_str})"], check=True)
subprocess.run(["git", "push", "origin", "main"], check=True)
print("🎉 發布完成！")
