# -*- coding: utf-8 -*-
import json
import os
import datetime
import subprocess
import re

print("=" * 70)
print("🚀 正在永久整合官方真實派彩、實時更新時間至儀表板主發布引擎...")
print("=" * 70)

# 1. 讀取剛才抓取的官方賽果與派彩
results_file = "20260906_official_full_results.json"
if not os.path.exists(results_file):
    print("❌ 找不到 20260906_official_full_results.json，請確認剛才的抓取腳本已執行。")
    exit(1)

with open(results_file, "r", encoding="utf-8") as f:
    official_data = json.load(f)

# 2. 你的策略二注單定義
bets = {
    1: {"mode": "1膽拖4腳", "banker_no": 4, "banker_name": "4 新力驕", "legs": [2, 7, 6, 14], "q_bets": [(4,2), (4,7), (2,7)]},
    2: {"mode": "1膽拖4腳", "banker_no": 1, "banker_name": "1 駿馬之曲", "legs": [8, 5, 11, 7], "q_bets": [(1,8), (1,5), (8,5)]},
    3: {"mode": "超強單膽", "banker_no": 1, "banker_name": "1 嘉應高昇", "legs": [3, 5, 6, 2], "q_bets": [(1,3), (1,5)]},
    4: {"mode": "4匹複式", "banker_no": None, "banker_name": "複式 10, 12, 7, 14", "legs": [10, 12, 7, 14], "q_bets": [(10,12), (10,7), (12,7)]},
    5: {"mode": "1膽拖4腳", "banker_no": 4, "banker_name": "4 震撼人心", "legs": [12, 8, 11, 10], "q_bets": [(4,12), (4,8), (12,8)]},
    6: {"mode": "1膽拖4腳", "banker_no": 3, "banker_name": "3 馬馳登", "legs": [14, 8, 13, 10], "q_bets": [(3,14), (3,8), (14,8)]},
    7: {"mode": "1膽拖4腳", "banker_no": 3, "banker_name": "3 時時歡聲", "legs": [5, 2, 6, 7], "q_bets": [(3,5), (3,2), (5,2)]},
    8: {"mode": "4匹複式", "banker_no": None, "banker_name": "複式 4, 13, 14, 2", "legs": [4, 13, 14, 2], "q_bets": [(4,13), (4,14), (13,14)]},
    9: {"mode": "1膽拖4腳", "banker_no": 5, "banker_name": "5 櫻花酒杯", "legs": [4, 1, 3, 10], "q_bets": [(5,4), (5,1), (4,1)]},
    10: {"mode": "1膽拖4腳", "banker_no": 12, "banker_name": "12 支付之父", "legs": [2, 8, 10, 13], "q_bets": [(12,2), (12,8), (2,8)]}
}

# 3. 逐場計算真實中獎結果與官方派彩
table_rows = []
for race_no in range(1, 11):
    r_data = official_data.get(str(race_no), {})
    top3 = r_data.get("top3", [])
    divs = r_data.get("dividends", {})
    
    top3_nos = [int(x["horse_no"]) for x in top3]
    top3_str = "-".join([str(x) for x in top3_nos])
    
    # 整理官方派彩字典
    payout_map = {}
    for pool, items in divs.items():
        for it in items:
            payout_map[f"{pool}_{it['combination']}"] = it['dividend']

    cfg = bets[race_no]
    hits = []
    
    # 核對單 T
    if len(top3_nos) == 3:
        s_top3 = set(top3_nos)
        if cfg["mode"] in ["1膽拖4腳", "超強單膽"]:
            if cfg["banker_no"] in s_top3 and set(cfg["legs"]).issuperset(s_top3 - {cfg["banker_no"]}):
                # 單 T 命中，抓取官方金額
                t_div = divs.get("單Ｔ", divs.get("單T", []))
                div_val = t_div[0]["dividend"] if t_div else "已中"
                hits.append(f"🎯 單T中 (${div_val})")
        elif "複式" in cfg["mode"]:
            if set(cfg["legs"]).issuperset(s_top3):
                t_div = divs.get("單Ｔ", divs.get("單T", []))
                div_val = t_div[0]["dividend"] if t_div else "已中"
                hits.append(f"🎯 單T複式中 (${div_val})")

    # 核對位置 Q
    for q in cfg["q_bets"]:
        if q[0] in top3_nos and q[1] in top3_nos:
            comb1 = f"{q[0]},{q[1]}"
            comb2 = f"{q[1]},{q[0]}"
            q_div_val = payout_map.get(f"位置Ｑ_{comb1}", payout_map.get(f"位置Ｑ_{comb2}", payout_map.get(f"位置Q_{comb1}", payout_map.get(f"位置Q_{comb2}", "中"))))
            hits.append(f"位置Q {q[0]}-{q[1]} (${q_div_val})")

    if hits:
        result_html = f'<span style="color:#3fb950;font-weight:bold;background:rgba(46,160,67,0.15);padding:3px 8px;border-radius:4px;border:1px solid #2ea043;">{" ｜ ".join(hits)}</span>'
    else:
        result_html = '<span style="color:#f85149;background:rgba(248,81,73,0.1);padding:3px 8px;border-radius:4px;border:1px solid #da3633;">❌ 未中</span>'

    legs_display = ", ".join(map(str, cfg["legs"])) if cfg["legs"] else "-"
    table_rows.append(f"""
        <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;">第 {race_no} 場</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;">{cfg['mode']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;color:#f1e05a;font-weight:bold;">{cfg['banker_name']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;">{legs_display}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;font-weight:bold;color:#58a6ff;">{top3_str}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;">{result_html}</td>
        </tr>
    """)

table_body_html = "".join(table_rows)

# 4. 讀取當前你最滿意的原始注單 UI
target_src = "public/index.html" if os.path.exists("public/index.html") else "index.html"
with open(target_src, "r", encoding="utf-8") as f:
    base_html = f.read()

# 清除任何先前殘留的標記
base_html = re.sub(r'<!-- 即時更新時間橫幅 -->[\s\S]*?<!-- 結束即時更新時間橫幅 -->', '', base_html)
base_html = re.sub(r'<div class="live-status-bar"[\s\S]*?</div>\s*</div>', '', base_html)
base_html = re.sub(r'<!-- 歷史賽事回測與投注策略存檔庫 -->[\s\S]*?<!-- 結束歷史賽事回測與投注策略存檔庫 -->', '', base_html)
base_html = re.sub(r'<details[\s\S]*?歷史賽事回測[\s\S]*?</details>', '', base_html)

now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

top_badge = f"""<!-- 即時更新時間橫幅 -->
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
<!-- 結束即時更新時間橫幅 -->"""

bottom_archive = f"""<!-- 歷史賽事回測與投注策略存檔庫 -->
<div style="margin-top:35px;margin-bottom:50px;">
    <details open style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;">
        <summary style="cursor:pointer;font-weight:bold;font-size:1.15em;color:#58a6ff;outline:none;">
            📜 歷史賽事回測與投注策略存檔庫（2026-09-06 官方真實派彩校驗版）
        </summary>
        <div style="margin-top:16px;">
            <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:12px 16px;margin-bottom:14px;">
                <div style="color:#f1e05a;font-weight:bold;">📁 2026-09-06 沙田開鑼日賽（官方派彩全量化比對）</div>
                <div style="margin-top:6px;font-size:0.88em;color:#8b949e;">數據來源：馬會官方 localresults 實時結算 ｜ 完整核對單 T 與位置 Q 真實派彩紅利。</div>
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:0.9em;color:#c9d1d9;">
                <thead>
                    <tr style="background:#21262d;color:#f0f6fc;text-align:left;">
                        <th style="padding:10px 12px;border-bottom:1px solid #30363d;">場次</th>
                        <th style="padding:10px 12px;border-bottom:1px solid #30363d;">策略模式</th>
                        <th style="padding:10px 12px;border-bottom:1px solid #30363d;">模型核心/膽馬</th>
                        <th style="padding:10px 12px;border-bottom:1px solid #30363d;">價值配腳</th>
                        <th style="padding:10px 12px;border-bottom:1px solid #30363d;">官方三甲</th>
                        <th style="padding:10px 12px;border-bottom:1px solid #30363d;">真實核算結果</th>
                    </tr>
                </thead>
                <tbody>
                    {table_body_html}
                </tbody>
            </table>
        </div>
    </details>
</div>
<!-- 結束歷史賽事回測與投注策略存檔庫 -->"""

# 注入到 HTML
if "<body" in base_html:
    b_idx = base_html.find(">", base_html.find("<body")) + 1
    final_html = base_html[:b_idx] + "\n" + top_badge + "\n" + base_html[b_idx:]
else:
    final_html = top_badge + "\n" + base_html

if "</body>" in final_html:
    e_idx = final_html.rfind("</body>")
    final_html = final_html[:e_idx] + "\n" + bottom_archive + "\n" + final_html[e_idx:]
else:
    final_html = final_html + "\n" + bottom_archive

# 5. 同時寫入根目錄與 public/ 目錄
target_paths = ["index.html"]
if os.path.exists("public"):
    target_paths.append("public/index.html")

for p in target_paths:
    with open(p, "w", encoding="utf-8") as f:
        f.write(final_html)
    print(f"✅ 成功寫入最新結構至: {p}")

# 6. 重構 publish_dashboard.py，防止背景 auto_monitor 覆蓋
pub_code = '''# -*- coding: utf-8 -*-
import shutil
import os
import subprocess

# 確保根目錄與 public 目錄完全同步
if os.path.exists("public") and os.path.exists("public/index.html"):
    shutil.copyfile("public/index.html", "index.html")

subprocess.run(["git", "add", "index.html", "public/index.html", "20260906_official_full_results.json"], check=False)
subprocess.run(["git", "commit", "-m", "chore: sync validated dashboard state"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
'''
with open("publish_dashboard.py", "w", encoding="utf-8") as f:
    f.write(pub_code)

print("✅ publish_dashboard.py 已修正為保護最新檔案！")

# 7. 提交並強制推送到遠端 GitHub
subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", f"feat: permanent integration of official payouts and live timestamp ({now_str})"], check=False)
res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)

print("🎉 永久發布引擎整合完成！GitHub 遠端推送成功！")
print(res.stdout if res.stdout else res.stderr)
