# -*- coding: utf-8 -*-
import json
import re
import subprocess
import os

with open("20260906_official_full_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 官方 1-10 場注單定義
bets = {
    1: {"mode": "1膽拖4腳", "banker": "4 新力驕", "banker_no": 4, "legs": [2, 7, 6, 14], "q_bets": [(4,2), (4,7), (2,7)]},
    2: {"mode": "1膽拖4腳", "banker": "1 駿馬之曲", "banker_no": 1, "legs": [8, 5, 11, 7], "q_bets": [(1,8), (1,5), (8,5)]},
    3: {"mode": "超強單膽", "banker": "1 嘉應高昇", "banker_no": 1, "legs": [3, 5, 6, 2], "q_bets": [(1,3), (1,5)]},
    4: {"mode": "4匹複式", "banker": "複式 10,12,7,14", "banker_no": None, "legs": [10, 12, 7, 14], "q_bets": [(10,12), (10,7), (12,7)]},
    5: {"mode": "1膽拖4腳", "banker": "4 震撼人心", "banker_no": 4, "legs": [12, 8, 11, 10], "q_bets": [(4,12), (4,8), (12,8)]},
    6: {"mode": "1膽拖4腳", "banker": "3 馬馳登", "banker_no": 3, "legs": [14, 8, 13, 10], "q_bets": [(3,14), (3,8), (14,8)]},
    7: {"mode": "1膽拖4腳", "banker": "3 時時歡聲", "banker_no": 3, "legs": [5, 2, 6, 7], "q_bets": [(3,5), (3,2), (5,2)]},
    8: {"mode": "4匹複式", "banker": "複式 4,13,14,2", "banker_no": None, "legs": [4, 13, 14, 2], "q_bets": [(4,13), (4,14), (13,14)]},
    9: {"mode": "1膽拖4腳", "banker": "5 櫻花酒杯", "banker_no": 5, "legs": [4, 1, 3, 10], "q_bets": [(5,4), (5,1), (4,1)]},
    10: {"mode": "1膽拖4腳", "banker": "12 支付之父", "banker_no": 12, "legs": [2, 8, 10, 13], "q_bets": [(12,2), (12,8), (2,8)]}
}

rows_html = []

for r_no in range(1, 11):
    r_info = data.get(str(r_no), {})
    top3 = r_info.get("top3", [])
    top3_nos = [int(x["horse_no"]) for x in top3]
    top3_str = "-".join(map(str, top3_nos))
    
    divs = r_info.get("dividends", {})
    
    # 解析官方所有派彩欄位，不論是全形半形
    t_payout = ""
    q_payout_map = {}
    
    for pool_k, items in divs.items():
        if "單" in pool_k and ("T" in pool_k or "Ｔ" in pool_k):
            if items:
                t_payout = items[0].get("dividend", "")
        if "位置" in pool_k and ("Q" in pool_k or "Ｑ" in pool_k):
            for item in items:
                c = item.get("combination", "")
                c_clean = tuple(sorted([int(x) for x in re.findall(r'\d+', c)]))
                if len(c_clean) == 2:
                    q_payout_map[c_clean] = item.get("dividend", "")

    cfg = bets[r_no]
    hits = []
    
    # 1. 驗證單 T
    if len(top3_nos) == 3:
        s_top3 = set(top3_nos)
        if cfg["banker_no"] and cfg["banker_no"] in s_top3 and set(cfg["legs"]).issuperset(s_top3 - {cfg["banker_no"]}):
            div_val = f" (${t_payout})" if t_payout else ""
            hits.append(f"🎯 單T命中{div_val}")
        elif not cfg["banker_no"] and set(cfg["legs"]).issuperset(s_top3):
            div_val = f" (${t_payout})" if t_payout else ""
            hits.append(f"🎯 單T命中{div_val}")
            
    # 2. 驗證位置 Q
    for q in cfg["q_bets"]:
        q_pair = tuple(sorted([q[0], q[1]]))
        if q[0] in top3_nos and q[1] in top3_nos:
            p_val = q_payout_map.get(q_pair, "")
            p_str = f" (${p_val})" if p_val else ""
            hits.append(f"命中位置Q: {q[0]}-{q[1]}{p_str}")

    if hits:
        result_text = f'<span style="color:#3fb950;font-weight:bold;">{" ｜ ".join(hits)}</span>'
    else:
        result_text = '<span style="color:#f85149;">❌ 未命中</span>'

    legs_display = ", ".join(map(str, cfg["legs"])) if cfg["banker_no"] else "-"
    rows_html.append(f"""
        <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;">第 {r_no} 場</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;">{cfg['mode']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;color:#f1e05a;">{cfg['banker']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;">{legs_display}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;">{top3_str}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #30363d;">{result_text}</td>
        </tr>
    """)

# 替換 HTML 內的表格內容
tbody_content = "".join(rows_html)

for target in ["public/index.html", "index.html"]:
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as f:
            html = f.read()
            
        # 精確替換 tbody 內的行
        html = re.sub(r'<tbody>[\s\S]*?</tbody>', f'<tbody>{tbody_content}</tbody>', html, count=1)
        
        with open(target, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ 已修正真實數值並寫入: {target}")

subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", "fix: parse exact dividend dollar amounts for all placed bets"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
print("🎉 精確派彩數字已全部同步推送至 GitHub Pages！")
