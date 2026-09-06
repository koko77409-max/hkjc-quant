# -*- coding: utf-8 -*-
import datetime
import subprocess
import os
import re

def update_and_push():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] 🚀 核心引擎正在更新儀表板並同步至 GitHub...")

    if not os.path.exists("index.html"):
        print("❌ 找不到 index.html！")
        return

    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # 1. 清理舊頂部橫幅
    html = re.sub(r'<!-- TOP_BAR -->[\s\S]*?<!-- TOP_BAR_END -->', '', html)
    html = re.sub(r'<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 20px;margin-bottom:20px[\s\S]*?最後實時更新[\s\S]*?</div>\s*</div>', '', html)

    # 2. 插入最新時間標籤
    clean_top = f"""<!-- TOP_BAR -->
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 20px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <div>
        <span style="font-size:1.15em;font-weight:bold;color:#f0f6fc;">🏇 HKJC 高頻量化決策監控中心</span>
        <span style="font-size:0.85em;color:#8b949e;margin-left:10px;">Harville 價值邊際 + IoT 微氣象跑道偏置引擎</span>
    </div>
    <div style="background:rgba(46,160,67,0.2);border:1px solid #3fb950;color:#3fb950;padding:6px 14px;border-radius:20px;font-weight:bold;font-size:0.95em;display:inline-flex;align-items:center;gap:8px;">
        <span style="width:8px;height:8px;background:#3fb950;border-radius:50%;box-shadow:0 0 8px #3fb950;"></span>
        最後實時更新：{now_str} (HKT)
    </div>
</div>
<!-- TOP_BAR_END -->"""

    if "<body" in html:
        b_idx = html.find(">", html.find("<body")) + 1
        html = html[:b_idx] + "\n" + clean_top + "\n" + html[b_idx:]
    else:
        html = clean_top + "\n" + html

    # 寫回唯一入口 index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    # 推送 GitHub
    subprocess.run(["git", "add", "index.html"], check=False)
    subprocess.run(["git", "commit", "-m", f"feat: live sync at {now_str}"], check=False)
    subprocess.run(["git", "push", "origin", "main"], check=False)
    print(f"[{now_str}] ✅ 儀表板已推送到 GitHub Pages！")

if __name__ == "__main__":
    update_and_push()
