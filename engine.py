# -*- coding: utf-8 -*-
import datetime
import subprocess
import os
import re

def update_and_push():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] 🚀 核心引擎執行更新...")

    if not os.path.exists("index.html"):
        return

    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # 正則更新時間
    html = re.sub(r'📡 模型同步時間：.*?\(HKT\)', f'📡 模型同步時間：{now_str} (HKT)', html)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    subprocess.run(["git", "add", "index.html"], check=False)
    subprocess.run(["git", "commit", "-m", f"chore: sync live timestamp {now_str}"], check=False)
    subprocess.run(["git", "push", "origin", "main"], check=False)
    print(f"[{now_str}] ✅ 已推送到 GitHub Pages！")

if __name__ == "__main__":
    update_and_push()
