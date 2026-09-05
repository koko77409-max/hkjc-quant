import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from live_smart_betslip import (
    load_model_artifacts,
    fetch_race_data,
    process_race_predictions,
    calculate_exotic_pools
)

def build_exotics_html_card(exotics):
    """渲染四重彩/四連環、孖T/三T、六寶獎卡片"""
    if not exotics:
        return ""
    
    html = """
    <div style="margin-bottom: 25px; background: linear-gradient(135deg, #1c1917 0%, #291e10 100%); border: 1px solid #f59e0b; border-radius: 12px; padding: 18px; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.15);">
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(245, 158, 11, 0.3); padding-bottom: 10px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px;">🎰</span>
                <span style="font-size: 16px; font-weight: bold; color: #fbbf24;">非對稱大彩池量化推薦 (Exotic Pools)</span>
            </div>
            <span style="font-size: 11px; background: #78350f; color: #fde68a; padding: 2px 8px; border-radius: 10px;">Henery 剪枝模型</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
    """
    
    # 四重彩 / 四連環
    if exotics.get('first4_quartet'):
        html += '<div style="background: rgba(0,0,0,0.4); border-radius: 8px; padding: 12px; border-left: 3px solid #3b82f6;">'
        html += '<div style="color: #60a5fa; font-weight: bold; font-size: 13px; margin-bottom: 6px;">🎯 四重彩 / 四連環剪枝</div>'
        for it in exotics['first4_quartet'][:3]:
            html += f"""
            <div style="margin-bottom: 8px; font-size: 12px; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 5px;">
                <span style="background: #1d4ed8; color: white; padding: 1px 5px; border-radius: 4px; font-size: 10px;">第 {it['race_no']} 場</span>
                <strong style="color: #f3f4f6; margin-left: 4px;">{it['pool']}</strong>
                <div style="color: #fef08a; font-family: monospace; font-size: 13px; margin: 3px 0;">{it['structure']}</div>
                <div style="color: #9ca3af; font-size: 11px;">注數: {it['bets_count']} 注 (${it['suggested_cost']}) | {it['edge_reason']}</div>
            </div>
            """
        html += '</div>'
        
    # 三T / 孖T
    html += '<div style="background: rgba(0,0,0,0.4); border-radius: 8px; padding: 12px; border-left: 3px solid #10b981;">'
    html += '<div style="color: #34d399; font-weight: bold; font-size: 13px; margin-bottom: 6px;">👑 孖 T / 三 T 膽拖</div>'
    if exotics.get('triple_trio'):
        tt = exotics['triple_trio'][0]
        html += f"""
        <div style="margin-bottom: 8px; font-size: 12px; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 5px;">
            <span style="background: #047857; color: white; padding: 1px 5px; border-radius: 4px; font-size: 10px;">三 T (R4-R5-R6)</span>
            <div style="color: #a7f3d0; font-family: monospace; font-size: 12px; margin: 3px 0;">{tt['structure']}</div>
            <div style="color: #9ca3af; font-size: 11px;">注數: {tt['bets_count']} 注 (${tt['suggested_cost']}) | {tt['note']}</div>
        </div>
        """
    if exotics.get('double_trio'):
        dt = exotics['double_trio'][0]
        html += f"""
        <div style="font-size: 12px;">
            <span style="background: #047857; color: white; padding: 1px 5px; border-radius: 4px; font-size: 10px;">孖 T (R4-R5)</span>
            <div style="color: #a7f3d0; font-family: monospace; font-size: 12px; margin: 3px 0;">{dt['structure']}</div>
            <div style="color: #9ca3af; font-size: 11px;">注數: {dt['bets_count']} 注 (${dt['suggested_cost']}) | {dt['note']}</div>
        </div>
        """
    html += '</div>'

    # 六寶獎
    if exotics.get('six_up'):
        six = exotics['six_up'][0]
        html += '<div style="background: rgba(0,0,0,0.4); border-radius: 8px; padding: 12px; border-left: 3px solid #a855f7;">'
        html += '<div style="color: #c084fc; font-weight: bold; font-size: 13px; margin-bottom: 6px;">⚡ 六寶獎 (Six-Up) 穿透路徑</div>'
        html += f"""
        <div style="font-size: 12px;">
            <span style="background: #7e22ce; color: white; padding: 1px 5px; border-radius: 4px; font-size: 10px;">R5 ~ R10</span>
            <div style="color: #e9d5ff; font-family: monospace; font-size: 12px; margin: 3px 0;">{six['structure']}</div>
            <div style="color: #9ca3af; font-size: 11px;">總注數: {six['bets_count']} 注 (${six['suggested_cost']}) | {six['note']}</div>
        </div>
        """
        html += '</div>'

    html += "</div></div>"
    return html

def main():
    model, features = load_model_artifacts()
    target_race_date = "2026/09/06"
    
    all_race_dfs = {}
    races_data = []
    
    for r_no in range(1, 11):
        df = fetch_race_data(target_race_date, r_no)
        if not df.empty:
            df_scored, bets = process_race_predictions(df, model, features, target_race_date, r_no)
            all_race_dfs[r_no] = df_scored
            races_data.append((r_no, df_scored, bets))
    
    # 渲染大彩池卡片
    exotics_data = calculate_exotic_pools(all_race_dfs)
    exotics_html = build_exotics_html_card(exotics_data)
    
    # 組合卡片與賽事詳情
    cards_html = ""
    for r_no, df_scored, bets in races_data:
        # 單場賽事卡片渲染
        cards_html += f"""
        <div class="race-card" style="background: #161b22; border: 1px solid #30363d; border-radius: 10px; margin-bottom: 20px; padding: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #21262d; padding-bottom: 8px; margin-bottom: 12px;">
                <h3 style="margin: 0; color: #58a6ff;">第 {r_no} 場</h3>
                <span style="font-size: 12px; color: #8b949e;">出賽馬匹: {len(df_scored)} 匹</span>
            </div>
        """
        # 注單推薦
        if bets:
            cards_html += '<div style="margin-bottom: 12px; background: #0d1117; padding: 10px; border-radius: 6px; border-left: 3px solid #f59e0b;">'
            for b in bets:
                h_str = " ".join(b.get('horses', [])) if isinstance(b.get('horses'), list) else str(b.get('horses'))
                cards_html += f"""
                <div style="font-size: 13px; margin-bottom: 4px; display: flex; justify-content: space-between;">
                    <span style="color: #ffaa00; font-weight: bold;">[{b.get('type')}] <span style="color: #f0f6fc;">{h_str}</span></span>
                    <span style="color: #7ee787; font-weight: bold;">建議注碼: ${b.get('stake', 10)}</span>
                </div>
                """
            cards_html += '</div>'
            
        # 馬匹排位表格
        cards_html += """
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                <thead>
                    <tr style="color: #8b949e; border-bottom: 1px solid #30363d;">
                        <th style="padding: 6px;">馬號</th>
                        <th>馬名</th>
                        <th>檔位</th>
                        <th>負磅</th>
                        <th>評分</th>
                        <th>體重(升降)</th>
                        <th>配備</th>
                        <th>即時獨贏</th>
                        <th>模型勝率</th>
                        <th>邊際優勢(Edge)</th>
                        <th>資金狀態</th>
                    </tr>
                </thead>
                <tbody>
        """
        for _, row in df_scored.iterrows():
            edge_val = row.get('edge', 0.0)
            edge_color = "#3fb950" if edge_val >= 1.0 else ("#f85149" if edge_val < 0.8 else "#c9d1d9")
            w_diff = str(row.get('weight_diff', ''))
            w_str = f"{row.get('body_weight', '-')} ({w_diff})" if row.get('body_weight') else "-"
            flow_status = row.get('flow_status', '')
            
            cards_html += f"""
                <tr style="border-bottom: 1px solid #21262d; color: #c9d1d9;">
                    <td style="padding: 6px; font-weight: bold; color: #58a6ff;">{row.get('horse_no')}</td>
                    <td style="font-weight: bold; color: #f0f6fc;">{row.get('horse_name')}</td>
                    <td>{row.get('draw', '-')}</td>
                    <td>{row.get('handicap_weight', '-')}</td>
                    <td>{row.get('rating', '-')}</td>
                    <td style="font-size: 11px;">{w_str}</td>
                    <td style="font-size: 11px; color: #d2a8ff;">{row.get('gear', '-')}</td>
                    <td style="font-weight: bold; color: #ffaa00;">{row.get('win_odds', 0.0):.1f}</td>
                    <td>{row.get('win_prob', 0.0)*100:.1f}%</td>
                    <td style="color: {edge_color}; font-weight: bold;">{edge_val:.2f}</td>
                    <td style="font-size: 11px;">{flow_status}</td>
                </tr>
            """
        cards_html += "</tbody></table></div>"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>香港賽馬量化實戰指南</title>
    <style>
        body {{
            background-color: #0d1117;
            color: #c9d1d9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 25px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <h2 style="margin: 0; color: #f0f6fc;">🏇 香港賽馬量化實戰指南</h2>
                <span style="font-size: 12px; color: #8b949e;">更新時間: {now_str}</span>
            </div>
            <div style="margin-top: 10px; display: flex; gap: 10px; font-size: 12px;">
                <span style="background: #da3633; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">香港本地</span>
                <span style="background: #238636; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">沙田 (ST)</span>
                <span style="color: #8b949e; align-self: center;">賽事日: {target_race_date}</span>
            </div>
        </div>

        {exotics_html}

        {cards_html}
    </div>
</body>
</html>
"""

    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    print("✅ 儀表板 HTML 生成成功 (含大彩池專區)！")

if __name__ == "__main__":
    main()
