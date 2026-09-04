from datetime import datetime, timezone, timedelta
import io
import os
import re
import sys
from auto_monitor import (
    get_odds_movement_summary,
    init_odds_table,
    scan_and_record_odds,
)
from live_smart_betslip import get_upcoming_local_race, run_smart_betslip
import pandas as pd

# 1. 偵測賽事並記錄最新盤口快照
target_race_date, target_venue = get_upcoming_local_race()
venue_text = '沙田 (ST)' if target_venue == 'ST' else '跑馬地 (HV)'
print(f'🏇 鎖定賽事: {target_race_date} {venue_text}')

init_odds_table()
scan_and_record_odds(target_race_date, target_venue)
movement_df = get_odds_movement_summary(target_race_date)

# 2. 捕捉量化推理輸出
old_stdout = sys.stdout
sys.stdout = buffer = io.StringIO()

try:
    run_smart_betslip(
        target_date=target_race_date,
        venue_code=target_venue,
        bankroll=10000.0,
    )
finally:
    raw_text = buffer.getvalue()
    sys.stdout = old_stdout

hkt_now = datetime.now(timezone(timedelta(hours=8))).strftime(
    '%Y-%m-%d %H:%M:%S'
)

# -------------------------------------------------------------
# 3. 解析四大實戰策略
# -------------------------------------------------------------

# 【策略一：+EV 獨贏】
strat1_html = ''
if '彩池尚未開售' in raw_text or '未開盤' in raw_text:
    strat1_html = """
    <div class="pending-box">
        <div class="pending-title">⏳ 彩池未開售（暫無賠率）</div>
        <div class="pending-desc">+EV 獨贏單注需在「賠率 1.5–3.0 且 Edge &ge; 1.00」甜蜜點下注，待週六開盤後自動鎖定。</div>
    </div>
    """
else:
    s1_items = re.findall(
        r'第\s*(\d+)\s*場\s*\|\s*(\S+)\s*號\s*(\S+)\s*\|\s*賠率:\s*(\S+)\s*\|\s*模型勝率:\s*(\S+)\s*\|\s*優勢'
        r' Edge:\s*(\S+)\s*\|\s*建議投注:\s*(\S+)',
        raw_text,
    )
    if s1_items:
        for r_no, h_no, name, odds, prob, edge, stake in s1_items:
            strat1_html += f"""
            <div class="win-bet-item">
                <div class="win-left">
                    <span class="race-tag">R{r_no}</span>
                    <span class="win-horse">{h_no}號 {name}</span>
                </div>
                <div class="win-right">
                    <span class="win-odds">賠率 {odds}</span>
                    <span class="win-stake">建議 {stake}</span>
                </div>
            </div>
            """
    else:
        strat1_html = '<div class="empty-note">今日暫無符合回測甜蜜點之獨贏標的。</div>'

# 【策略二：Top 3 互串 (QP Box + 單 T)】
s2_matches = re.finditer(
    r'第\s*(\d+)\s*場核心三甲\s*:\s*([^\n]+)\n\s*[├\+\-]?\s*🥈\s*位置 Q'
    r' 互串[^\:]*:\s*\[(.*?)\]\s*\((.*?)\)\n\s*[└\+\-]?\s*🥇\s*單'
    r' T[^\:]*:\s*\[(.*?)\]\s*\((.*?)\)',
    raw_text,
)

strat2_cards_html = ''
for m in s2_matches:
    r_no, horses_str, qp_str, qp_cost, trio_str, trio_cost = m.groups()

    h_tags = ''
    for h in horses_str.split('+'):
        h_clean = h.strip()
        h_tags += f'<span class="h-chip">{h_clean}</span>'

    qp_chips = ''
    for p in qp_str.split(','):
        p_clean = p.strip()
        qp_chips += f'<span class="bet-chip">{p_clean}</span>'

    cost_qp_match = re.search(r'共\s*(\$\d+)', qp_cost)
    cost_qp_txt = cost_qp_match.group(1) if cost_qp_match else '$30'

    strat2_cards_html += f"""
    <div class="ticket-card">
        <div class="ticket-header">
            <span class="race-tag-lg">第 {r_no} 場</span>
            <div class="h-chips-wrap">{h_tags}</div>
        </div>
        <div class="ticket-body">
            <div class="ticket-row">
                <span class="bet-badge qp">位置 Q</span>
                <div class="chips-list">{qp_chips}</div>
                <span class="ticket-price">3注 {cost_qp_txt}</span>
            </div>
            <div class="ticket-row">
                <span class="bet-badge trio">單 T</span>
                <div class="chips-list"><span class="bet-chip trio-chip">{trio_str.strip()}</span></div>
                <span class="ticket-price">1注 $10</span>
            </div>
        </div>
    </div>
    """

# 【策略三：超級穩膽】
s3_match = re.search(
    r'第\s*(\d+)\s*場\s*\|\s*超強單膽:\s*([^\(]+)\(純勝率:\s*([^\)]+)\)\n\s*[└\+\-]?\s*單膽拖腳:\s*([^\n\(]+)\((.*?)\)',
    raw_text,
)
if s3_match:
    b_race, b_horse, b_prob, legs_str, b_cost = s3_match.groups()
    strat3_html = f"""
    <div class="banker-card">
        <div class="banker-header">
            <span class="race-tag-lg">第 {b_race} 場</span>
            <span class="banker-badge">超強單膽</span>
            <span class="banker-horse">{b_horse.strip()}</span>
            <span class="banker-prob">勝率 {b_prob.strip()}</span>
        </div>
        <div class="banker-legs">拖腳：<strong>{legs_str.strip()}</strong></div>
        <div class="banker-cost">Q 及 QP 各買 2 注 (每注 $20，共 $80)</div>
    </div>
    """
else:
    strat3_html = (
        '<div class="empty-note">今日無勝率超過 28% 的超級單膽場次。</div>'
    )

# 【策略四：位置過關 3 串 4】
s4_legs = re.findall(
    r'關次:\s*第\s*(\d+)\s*場\s*\|\s*(\S+)\s*號\s*(\S+)\s*\(純勝率:\s*([^\)]+)\)',
    raw_text,
)
strat4_html = ''
if len(s4_legs) >= 3:
    legs_html = ''
    for r_no, h_no, name, prob in s4_legs:
        legs_html += f"""
        <div class="allup-step">
            <span class="allup-tag">R{r_no}</span>
            <span class="allup-horse">{h_no}號 {name}</span>
            <span class="allup-prob">勝率 {prob}</span>
        </div>
        """
    strat4_html = f"""
    <div class="allup-card">
        <div class="allup-steps">{legs_html}</div>
        <div class="allup-summary">
            <span>3 串 4 位置 (PLACE)</span>
            <span class="allup-stake">建議每注 $50 (總成本 $200)</span>
        </div>
    </div>
    """

# -------------------------------------------------------------
# 4. 解析賽事排行榜與掛載賠率走勢標籤
# -------------------------------------------------------------
race_matches = list(
    re.finditer(
        r'🏇【\s*第\s*(\d+)\s*場\s*】（共\s*(\d+)\s*匹馬）\n-+\n.*?\n-+\n(.*?)(?=(?:🏇【|🎫|===|\Z))',
        raw_text,
        re.S,
    )
)

races_html = ''
nav_buttons = ''

for rm in race_matches:
    r_no = rm.group(1)
    h_count = rm.group(2)
    body = rm.group(3).strip()

    nav_buttons += f'<a href="#race-{r_no}" class="nav-pill">R{r_no}</a>'
    rows_html = ''

    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(
            r'^\s*第\s*(\d+)\s*名\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)',
            line,
        )
        if m:
            (
                rank,
                h_no,
                name,
                draw,
                jockey,
                odds,
                m_pct,
                mkt_pct,
                edge,
            ) = m.groups()
            rank_int = int(rank)
            rank_class = f'rank-{rank_int}' if rank_int <= 3 else 'rank-other'
            badge = f'<span class="rank-badge {rank_class}">{rank_int}</span>'

            # 檢索該馬匹的賠率走勢
            trend_badge = ''
            if not movement_df.empty:
                m_row = movement_df[
                    (movement_df['race_no'] == int(r_no))
                    & (movement_df['horse_no'] == str(h_no))
                ]
                if not m_row.empty:
                    drop = m_row.iloc[0]['drop_pct']
                    cnt = m_row.iloc[0]['records_count']
                    if cnt > 1:
                        if drop >= 15.0:
                            trend_badge = f'<span class="trend-badge drop">⚡大戶 -{abs(drop):.0f}%</span>'
                        elif drop <= -15.0:
                            trend_badge = f'<span class="trend-badge drift">↗漂冷 +{abs(drop):.0f}%</span>'

            rows_html += f"""
            <tr>
                <td>{badge}</td>
                <td class="td-bold">{h_no}</td>
                <td class="td-bold td-name">{name}{trend_badge}</td>
                <td>{draw}</td>
                <td>{jockey}</td>
                <td class="td-odds">{odds}</td>
                <td class="td-prob">{m_pct}</td>
                <td class="td-edge">{edge}</td>
            </tr>
            """

    races_html += f"""
    <div class="race-table-card" id="race-{r_no}">
        <div class="race-table-header">
            <span>🏇 第 {r_no} 場</span>
            <span class="race-h-count">{h_count} 匹馬</span>
        </div>
        <div class="table-scroller">
            <table>
                <thead>
                    <tr>
                        <th>名次</th><th>馬號</th><th style="text-align:left;padding-left:8px;">馬名 / 資金動向</th><th>檔位</th><th>騎師</th><th>賠率</th><th>勝率</th><th>Edge</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>
    """

# -------------------------------------------------------------
# 5. 輸出深色手機專屬原生網頁
# -------------------------------------------------------------
html_template = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>🏇 香港賽馬量化實戰指南</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #0b0c10;
            color: #e0e2ec;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang HK", sans-serif;
            padding: 12px 10px 48px 10px;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        
        .top-header {{
            background: linear-gradient(135deg, #181a20, #14161c);
            padding: 14px 16px;
            border-radius: 14px;
            border-left: 4px solid #00e676;
            margin-bottom: 16px;
            border-top: 1px solid #232732;
            border-right: 1px solid #232732;
            border-bottom: 1px solid #232732;
        }}
        .top-header h1 {{
            font-size: 1.15rem;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 6px;
            letter-spacing: 0.5px;
        }}
        .meta-line {{
            font-size: 0.76rem;
            color: #8b92a5;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .badge-hk {{ background: #ef4444; color: #fff; padding: 2px 7px; border-radius: 6px; font-weight: 700; font-size: 0.7rem; }}
        .badge-venue {{ background: #00e676; color: #000; padding: 2px 7px; border-radius: 6px; font-weight: 800; font-size: 0.7rem; }}

        .section-header {{
            display: flex;
            align-items: center;
            font-size: 0.92rem;
            font-weight: 800;
            color: #fff;
            margin: 18px 2px 8px 2px;
        }}
        .strat-sub {{
            font-size: 0.72rem;
            color: #8b92a5;
            margin: -4px 2px 10px 4px;
        }}

        .pending-box {{
            background: #151821;
            border: 1px solid #232838;
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 14px;
        }}
        .pending-title {{ color: #fbbf24; font-weight: 700; font-size: 0.82rem; margin-bottom: 4px; }}
        .pending-desc {{ color: #8b92a5; font-size: 0.74rem; line-height: 1.4; }}
        .win-bet-item {{
            background: #151821;
            border: 1px solid #232838;
            border-radius: 12px;
            padding: 10px 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .race-tag {{ background: #2563eb; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.72rem; }}
        .win-horse {{ font-weight: 700; color: #fff; font-size: 0.88rem; margin-left: 6px; }}
        .win-odds {{ color: #38bdf8; font-size: 0.82rem; font-weight: 700; margin-right: 12px; }}
        .win-stake {{ color: #00e676; font-size: 0.82rem; font-weight: 800; }}

        .ticket-card {{
            background: #151821;
            border: 1px solid #232838;
            border-radius: 12px;
            margin-bottom: 10px;
            padding: 10px 12px;
        }}
        .ticket-header {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px dashed #282e40;
            gap: 8px;
        }}
        .race-tag-lg {{
            background: #2563eb;
            color: #fff;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 800;
            white-space: nowrap;
        }}
        .h-chips-wrap {{ display: flex; flex-wrap: wrap; gap: 4px; }}
        .h-chip {{
            background: #202534;
            color: #e2e8f0;
            padding: 2px 6px;
            border-radius: 5px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .ticket-body {{ display: flex; flex-direction: column; gap: 6px; }}
        .ticket-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.76rem;
            gap: 6px;
        }}
        .bet-badge {{
            font-size: 0.68rem;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 5px;
            white-space: nowrap;
        }}
        .bet-badge.qp {{ background: #475569; color: #f1f5f9; }}
        .bet-badge.trio {{ background: #b45309; color: #fef3c7; }}
        .chips-list {{ display: flex; flex-wrap: wrap; gap: 4px; flex: 1; margin: 0 4px; }}
        .bet-chip {{
            background: #1c2230;
            color: #38bdf8;
            border: 1px solid #2d374d;
            padding: 1px 6px;
            border-radius: 4px;
            font-family: ui-monospace, Menlo, monospace;
            font-size: 0.72rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .trio-chip {{ color: #fbbf24; border-color: #5c441b; }}
        .ticket-price {{ color: #94a3b8; font-size: 0.72rem; font-weight: 700; white-space: nowrap; }}

        .banker-card {{
            background: #1a1625;
            border: 1px solid #4c2882;
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 12px;
        }}
        .banker-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
        .banker-badge {{ background: #9333ea; color: #fff; padding: 2px 6px; border-radius: 5px; font-size: 0.7rem; font-weight: 800; }}
        .banker-horse {{ font-weight: 800; color: #fff; font-size: 0.9rem; }}
        .banker-prob {{ color: #00e676; font-size: 0.75rem; font-weight: 700; margin-left: auto; }}
        .banker-legs {{ font-size: 0.76rem; color: #d8b4fe; margin-bottom: 4px; }}
        .banker-cost {{ font-size: 0.72rem; color: #94a3b8; }}

        .allup-card {{
            background: #151821;
            border: 1px solid #232838;
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 16px;
        }}
        .allup-steps {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }}
        .allup-step {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.78rem;
            background: #1c202c;
            padding: 6px 10px;
            border-radius: 8px;
        }}
        .allup-tag {{ background: #3b82f6; color: #fff; padding: 1px 6px; border-radius: 4px; font-weight: 800; font-size: 0.7rem; }}
        .allup-horse {{ font-weight: 700; color: #fff; flex: 1; margin-left: 8px; }}
        .allup-prob {{ color: #00e676; font-weight: 700; font-size: 0.74rem; }}
        .allup-summary {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: #fbbf24;
            font-weight: 700;
            padding-top: 6px;
            border-top: 1px dashed #282e40;
        }}
        .allup-stake {{ color: #94a3b8; font-weight: normal; }}

        .nav-scroller {{
            display: flex;
            overflow-x: auto;
            gap: 6px;
            padding: 4px 2px 10px 2px;
            margin-bottom: 12px;
            -webkit-overflow-scrolling: touch;
        }}
        .nav-pill {{
            flex: 0 0 auto;
            background: #1c202c;
            color: #00e676;
            text-decoration: none;
            font-weight: 800;
            font-size: 0.76rem;
            padding: 5px 11px;
            border-radius: 8px;
            border: 1px solid #293042;
        }}

        .race-table-card {{
            background: #151821;
            border-radius: 12px;
            margin-bottom: 14px;
            border: 1px solid #232838;
            overflow: hidden;
        }}
        .race-table-header {{
            background: #1c202c;
            padding: 9px 12px;
            font-size: 0.88rem;
            font-weight: 800;
            color: #fff;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #282e40;
        }}
        .race-h-count {{ font-size: 0.72rem; color: #8b92a5; font-weight: normal; }}
        .table-scroller {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.76rem;
            white-space: nowrap;
            text-align: center;
        }}
        th {{
            background: #11141c;
            color: #8b92a5;
            font-weight: 600;
            padding: 7px 6px;
            font-size: 0.7rem;
            border-bottom: 1px solid #232838;
        }}
        td {{
            padding: 8px 6px;
            border-bottom: 1px solid #1c202c;
            color: #cbd5e1;
        }}
        .rank-badge {{
            display: inline-block;
            width: 18px;
            height: 18px;
            line-height: 18px;
            border-radius: 50%;
            font-weight: 800;
            font-size: 0.68rem;
        }}
        .rank-1 {{ background: #facc15; color: #000; }}
        .rank-2 {{ background: #94a3b8; color: #000; }}
        .rank-3 {{ background: #f97316; color: #000; }}
        .rank-other {{ background: #242a38; color: #64748b; }}
        .td-bold {{ font-weight: 700; color: #fff; }}
        .td-name {{ text-align: left; padding-left: 6px; font-weight: 700; }}
        .td-odds {{ color: #38bdf8; }}
        .td-prob {{ color: #00e676; font-weight: 800; }}
        .td-edge {{ color: #f43f5e; font-weight: 700; }}
        .empty-note {{ font-size: 0.74rem; color: #64748b; padding: 6px 4px; }}

        /* 資金異動動態 Badge */
        .trend-badge {{
            display: inline-block;
            margin-left: 4px;
            padding: 1px 4px;
            border-radius: 4px;
            font-size: 0.65rem;
            font-weight: 800;
            white-space: nowrap;
        }}
        .trend-badge.drop {{ background: #b91c1c; color: #fef2f2; border: 1px solid #ef4444; }}
        .trend-badge.drift {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="top-header">
            <h1>🏇 香港賽馬量化實戰指南</h1>
            <div class="meta-line">
                <span class="badge-hk">香港本地</span>
                <span class="badge-venue">{venue_text}</span>
                <span>賽事日：<strong>{target_race_date}</strong></span>
                <span>| {hkt_now} 更新</span>
            </div>
        </div>

        <div class="section-header">🎯 策略一：+EV 獨贏單注</div>
        <div class="strat-sub">回測 ROI +2.24% 甜蜜點（勝率 &ge; 25% | Edge &ge; 1.00）</div>
        {strat1_html}

        <div class="section-header">🛡️ 策略三：超級穩膽（單膽連贏 Q / QP）</div>
        {strat3_html}

        <div class="section-header">🚀 策略四：穩健位置過關（3 串 4）</div>
        {strat4_html}

        <div class="section-header">⚡ 策略二：每場 Top 3 互串（QP + 單 T）</div>
        <div class="strat-sub">QP 互串命中率 36.2%（每 2.8 場中 1 次）</div>
        {strat2_cards_html}

        <div class="section-header" style="margin-top:24px;">📋 各場排位勝率完整榜</div>
        <div class="nav-scroller">
            {nav_buttons}
        </div>
        {races_html}
    </div>
</body>
</html>
"""

os.makedirs('public', exist_ok=True)
with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

print(
    f'✅ 成功生成【香港本地賽事 {target_race_date} {venue_text}】動態賠率版手機網頁'
    ' public/index.html'
)