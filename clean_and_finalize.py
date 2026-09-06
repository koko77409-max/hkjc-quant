# -*- coding: utf-8 -*-
import json
import re
import subprocess
import os
import datetime

print("=" * 65)
print("🧹 正在清理重複頂部橫幅，並精確填入位置 Q 官方派彩金額...")
print("=" * 65)

# 讀取官方原始賽果與派彩 json
with open("20260906_official_full_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 建立每場位置 Q 的精確對照字典 {(race, min_no, max_no): dividend}
q_payout_table = {}
for r_str, r_info in data.items():
    r_no = int(r_str)
    divs = r_info.get("dividends", {})
    for pool_k, items in divs.items():
        if "位置" in pool_k and ("Q" in pool_k or "Ｑ" in pool_k):
            for it in items:
                comb = it.get("combination", "")
                nos = [int(x) for x in re.findall(r'\d+', comb)]
                if len(nos) == 2:
                    pair = (r_no, min(nos), max(nos))
                    q_payout_table[pair] = it.get("dividend", "")

now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 單一、乾淨的頂部橫幅
single_top_bar = f"""<!-- TOP_BAR_START -->
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

targets = ["public/index.html", "index.html"] if os.path.exists("public") else ["index.html"]

for t in targets:
    if not os.path.exists(t):
        continue
        
    with open(t, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. 徹底清除所有重複的頂部狀態條
    html = re.sub(r'<!-- TOP_BAR_START -->[\s\S]*?<!-- TOP_BAR_END -->', '', html)
    html = re.sub(r'<!-- 即時更新時間橫幅 -->[\s\S]*?<!-- 結束即時更新時間橫幅 -->', '', html)
    html = re.sub(r'<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:1[24]px 20px[\s\S]*?最后?實時更新[\s\S]*?</div>\s*</div>', '', html)
    html = re.sub(r'<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 20px;margin-bottom:20px[\s\S]*?</div>\s*</div>', '', html)

    # 2. 將乾淨的頂部橫幅注入到 <body> 最前端
    if "<body" in html:
        b_idx = html.find(">", html.find("<body")) + 1
        html = html[:b_idx] + "\n" + single_top_bar + "\n" + html[b_idx:]
    else:
        html = single_top_bar + "\n" + html

    # 3. 逐一將殘留的 ($中) 替換為真實派彩
    # R1: 位置Q 2-7
    r1_div = q_payout_table.get((1, 2, 7), "")
    if r1_div:
        html = re.sub(r'位置Q:?\s*2-7\s*\(\$中\)', f'位置Q 2-7 (${r1_div})', html)
        
    # R4: 位置Q 10-7
    r4_div = q_payout_table.get((4, 7, 10), "")
    if r4_div:
        html = re.sub(r'位置Q:?\s*10-7\s*\(\$中\)', f'位置Q 10-7 (${r4_div})', html)
        
    # R6: 位置Q 3-8
    r6_div = q_payout_table.get((6, 3, 8), "")
    if r6_div:
        html = re.sub(r'位置Q:?\s*3-8\s*\(\$中\)', f'位置Q 3-8 (${r6_div})', html)

    # 4. 寫回檔案
    with open(t, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已完成修復與寫入: {t}")

# 提交並推送到 GitHub
subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", "fix: remove duplicate header and populate exact Place Q dividends"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
print("🎉 清理與派彩數字補全已成功推送到 GitHub！")
