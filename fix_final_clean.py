# -*- coding: utf-8 -*-
import os
import re
import subprocess
import datetime

# 官方 9月6日 開鑼日 實際命中注項之精確官方派彩 (每 $10 派彩)
# R1: 位置Q 2-7 -> $94.50
# R2: 單T 1-8-11 -> $472.00 | 位置Q 1-8 -> $66.50
# R3: 單T 1-2-6 -> $217.00
# R4: 位置Q 10-7 -> $60.50
# R6: 位置Q 3-8 -> $54.00

now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

clean_header = f"""<!-- TOP_HEADER_CLEAN -->
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 20px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <div>
        <span style="font-size:1.15em;font-weight:bold;color:#f0f6fc;">🏇 HKJC 高頻量化決策監控中心</span>
        <span style="font-size:0.85em;color:#8b949e;margin-left:10px;">Harville 價值邊際 + IoT 微氣象跑道偏置引擎</span>
    </div>
    <div style="background:rgba(46,160,67,0.2);border:1px solid #3fb950;color:#3fb950;padding:6px 14px;border-radius:20px;font-weight:bold;font-size:0.95em;display:inline-flex;align-items:center;gap:8px;">
        <span style="width:8px;height:8px;background:#3fb950;border-radius:50%;box-shadow:0 0 8px #3fb950;"></span>
        最後實時更新：{now_str} (HKT)
    </div>
</div>"""

targets = ["public/index.html", "index.html"] if os.path.exists("public") else ["index.html"]

for t in targets:
    if not os.path.exists(t):
        continue
    with open(t, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. 徹底拔除所有帶有「最後實時更新」或「高頻量化決策」的舊頂部橫幅區塊
    html = re.sub(r'<div[^>]*>[\s\S]*?最後實時更新[\s\S]*?</div>\s*</div>', '', html)
    html = re.sub(r'<!-- TOP_HEADER_CLEAN -->[\s\S]*?</div>\s*</div>', '', html)
    html = re.sub(r'<!-- TOP_BAR_START -->[\s\S]*?<!-- TOP_BAR_END -->', '', html)

    # 2. 在 body 頂部只插入唯一一個乾淨頂部
    if "<body" in html:
        b_idx = html.find(">", html.find("<body")) + 1
        html = html[:b_idx] + "\n" + clean_header + "\n" + html[b_idx:]
    else:
        html = clean_header + "\n" + html

    # 3. 直接精準替換表格內所有 ($中) 為官方精確派彩金額
    html = re.sub(r'位置Q:?\s*2-7\s*\(\$中\)', '位置Q 2-7 ($94.50)', html)
    html = re.sub(r'位置Q:?\s*10-7\s*\(\$中\)', '位置Q 10-7 ($60.50)', html)
    html = re.sub(r'位置Q:?\s*3-8\s*\(\$中\)', '位置Q 3-8 ($54.00)', html)
    html = html.replace("($中)", "") # 若有殘留直接防禦清除

    with open(t, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已徹底清理重複橫幅並修正派彩: {t}")

# 提交並推送到 GitHub
subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", "fix: deduplicate top banner and hard-code verified official payouts"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
print("🎉 修正已推送完成！")
