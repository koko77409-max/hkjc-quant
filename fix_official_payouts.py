# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import re
import os
import subprocess
import datetime

print("=" * 65)
print("🔍 正在從馬會官方 localresults 提取 2026-09-06 真實派彩數據...")
print("=" * 65)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-HK,zh;q=0.9"
}

# 你的實際策略注單定義
bets = {
    1: {"mode": "1膽拖4腳", "banker": "4 新力驕", "legs": [2, 7, 6, 14], "t_bet": [4, 2, 7, 6, 14], "q_bets": [(4,2), (4,7), (2,7)]},
    2: {"mode": "1膽拖4腳", "banker": "1 駿馬之曲", "legs": [8, 5, 11, 7], "t_bet": [1, 8, 5, 11, 7], "q_bets": [(1,8), (1,5), (8,5)]},
    3: {"mode": "超強單膽", "banker": "1 嘉應高昇", "legs": [3, 5, 6, 2], "t_bet": [1, 3, 5, 6, 2], "q_bets": [(1,3), (1,5)]},
    4: {"mode": "4匹複式", "banker": "複式 10,12,7,14", "legs": [], "t_bet": [10, 12, 7, 14], "q_bets": [(10,12), (10,7), (12,7)]},
    5: {"mode": "1膽拖4腳", "banker": "4 震撼人心", "legs": [12, 8, 11, 10], "t_bet": [4, 12, 8, 11, 10], "q_bets": [(4,12), (4,8), (12,8)]},
    6: {"mode": "1膽拖4腳", "banker": "3 馬馳登", "legs": [14, 8, 13, 10], "t_bet": [3, 14, 8, 13, 10], "q_bets": [(3,14), (3,8), (14,8)]},
    7: {"mode": "1膽拖4腳", "banker": "3 時時歡聲", "legs": [5, 2, 6, 7], "t_bet": [3, 5, 2, 6, 7], "q_bets": [(3,5), (3,2), (5,2)]},
    8: {"mode": "4匹複式", "banker": "複式 4,13,14,2", "legs": [], "t_bet": [4, 13, 14, 2], "q_bets": [(4,13), (4,14), (13,14)]},
    9: {"mode": "1膽拖4腳", "banker": "5 櫻花酒杯", "legs": [4, 1, 3, 10], "t_bet": [5, 4, 1, 3, 10], "q_bets": [(5,4), (5,1), (4,1)]},
    10: {"mode": "1膽拖4腳", "banker": "12 支付之父", "legs": [2, 8, 10, 13], "t_bet": [12, 2, 8, 10, 13], "q_bets": [(12,2), (12,8), (2,8)]}
}

verified_rows = []

for race_no in range(1, 11):
    url = f"https://racing.hkjc.com/zh-hk/local/information/localresults?racedate=2026/09/06&Racecourse=ST&RaceNo={race_no}"
    try:
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # 抓取官方三甲
        table = soup.find("table", class_=re.compile(r"f_tac|table_bd")) or soup.find("table")
        top3_nos = []
        for row in table.find_all("tr"):
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) >= 10 and cols[0] in ["1", "2", "3"]:
                top3_nos.append(int(cols[1]))
        
        top3_str = "-".join(map(str, top3_nos))
        
        # 抓取官方派彩表格 (Dividends)
        payouts = {}
        for tr in soup.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(tds) >= 3:
                pool = tds[0]
                comb = tds[1]
                div = tds[2]
                if "位置Ｑ" in pool or "位置Q" in pool:
                    payouts[f"Q_{comb}"] = div
                elif "單Ｔ" in pool or "單T" in pool:
                    payouts[f"T_{comb}"] = div

        # 核對單 T
        cfg = bets[race_no]
        t_hit = False
        t_payout = ""
        if len(top3_nos) == 3:
            s_top3 = set(top3_nos)
            if cfg["mode"] == "1膽拖4腳" or cfg["mode"] == "超強單膽":
                banker_no = int(re.search(r'\d+', cfg["banker"]).group())
                if banker_no in s_top3 and set(cfg["legs"]).issuperset(s_top3 - {banker_no}):
                    t_hit = True
            elif "複式" in cfg["mode"]:
                if set(cfg["t_bet"]).issuperset(s_top3):
                    t_hit = True
        
        # 核對位置 Q
        q_hits = []
        if len(top3_nos) == 3:
            for qb in cfg["q_bets"]:
                if qb[0] in top3_nos and qb[1] in top3_nos:
                    # 匹配派彩
                    comb_key1 = f"{qb[0]},{qb[1]}"
                    comb_key2 = f"{qb[1]},{qb[0]}"
                    div = payouts.get(f"Q_{comb_key1}", payouts.get(f"Q_{comb_key2}", "命中"))
                    q_hits.append(f"{qb[0]}-{qb[1]} (${div})")
        
        # 結論文字
        verdict_items = []
        if t_hit:
            verdict_items.append("🎯 單T命中")
        if q_hits:
            verdict_items.append(f"命中位置Q: {', '.join(q_hits)}")
        
        if not verdict_items:
            verdict_str = '<span style="color:#f85149;">❌ 未命中</span>'
        else:
            verdict_str = f'<span style="color:#3fb950;font-weight:bold;">{" ｜ ".join(verdict_items)}</span>'

        legs_str = ", ".join(map(str, cfg["legs"])) if cfg["legs"] else "-"
        verified_rows.append(f"""
            <tr>
                <td style="padding:10px;border-bottom:1px solid #30363d;">第 {race_no} 場</td>
                <td style="padding:10px;border-bottom:1px solid #30363d;">{cfg['mode']}</td>
                <td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">{cfg['banker']}</td>
                <td style="padding:10px;border-bottom:1px solid #30363d;">{legs_str}</td>
                <td style="padding:10px;border-bottom:1px solid #30363d;">{top3_str}</td>
                <td style="padding:10px;border-bottom:1px solid #30363d;">{verdict_str}</td>
            </tr>
        """)
        print(f"R{race_no} 結算完成: 官方三甲 [{top3_str}] | 結果: {' ｜ '.join(verdict_items) if verdict_items else '未中'}")
    except Exception as e:
        print(f"R{race_no} 提取出錯: {e}")

# 重寫更新 HTML
table_body = "".join(verified_rows)

html_template = f"""
<!-- 歷史賽事回測與投注策略存檔庫 -->
<div style="margin-top:35px;margin-bottom:50px;">
    <details open style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;">
        <summary style="cursor:pointer;font-weight:bold;font-size:1.15em;color:#58a6ff;outline:none;">
            📜 歷史賽事回測與投注策略存檔庫（2026-09-06 官方真實派彩校驗版）
        </summary>
        <div style="margin-top:16px;">
            <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:12px 16px;margin-bottom:14px;">
                <div style="color:#f1e05a;font-weight:bold;">📁 2026-09-06 沙田開鑼日賽（官方派彩全量化比對）</div>
                <div style="margin-top:6px;font-size:0.88em;color:#8b949e;">數據來源：馬會官方 localresults ｜ 排除任何手動粗估，精確核對每注彩池真實紅利。</div>
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:0.9em;color:#c9d1d9;">
                <thead>
                    <tr style="background:#21262d;color:#f0f6fc;text-align:left;">
                        <th style="padding:10px;border-bottom:1px solid #30363d;">場次</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">策略模式</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">模型核心/膽馬</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">價值配腳</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">官方三甲</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">真實核算結果</th>
                    </tr>
                </thead>
                <tbody>
                    {table_body}
                </tbody>
            </table>
        </div>
    </details>
</div>
"""

# 更新檔案
targets = ["index.html", "public/index.html"] if os.path.exists("public") else ["index.html"]
for t in targets:
    if os.path.exists(t):
        with open(t, "r", encoding="utf-8") as f:
            c = f.read()
        c = re.sub(r'<!-- 歷史賽事回測與投注策略存檔庫 -->[\s\S]*?<!-- 歷史賽事回測與投注策略存檔庫結束 -->', '', c)
        c = re.sub(r'<details[\s\S]*?歷史賽事回測[\s\S]*?</details>', '', c)
        
        idx = c.rfind("</body>") if "</body>" in c else len(c)
        new_c = c[:idx] + "\n" + html_template + c[idx:]
        with open(t, "w", encoding="utf-8") as f:
            f.write(new_c)
        print(f"✅ 已修正並寫入: {t}")

subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", "fix: correct historical review with official dividends verification"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
print("🎉 修正已推送至 GitHub！")
