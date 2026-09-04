from datetime import datetime, timezone, timedelta
import io
import os
import re
import sys
from live_smart_betslip import get_upcoming_local_race, run_smart_betslip

# 1. 自動鎖定香港本地賽事
target_race_date, target_venue = get_upcoming_local_race()
venue_text = '沙田 (ST)' if target_venue == 'ST' else '跑馬地 (HV)'
print(f'🏇 鎖定賽事: {target_race_date} {venue_text}')

# 2. 捕捉推理輸出
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

# 3. 解析策略與賽事為原生 HTML
strat_cards_html = ''
strat_match = re.search(r'🎫\s*香港.*?策略核心.*?\n=+\n(.*)', raw_text, re.S)
if strat_match:
    strat_text = strat_match.group(1).strip()
    strat_blocks = re.findall(
        r'(【\s*[^】]+】.*?)(?=(?:【|\Z))', strat_text, re.S
    )
    for sb in strat_blocks:
        lines = sb.strip().split('\n')
        title = lines[0].strip()
        content = '\n'.join(lines[1:]).strip()
        strat_cards_html += f"""
        <div class="strategy-card">
            <div class="strategy-title">{title}</div>
            <pre class="strategy-content">{content}</pre>
        </div>
        """

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

    nav_buttons += f'<a href="#race-{r_no}" class="nav-btn">R{r_no}</a>'
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

            rows_html += f"""
            <tr>
                <td>{badge}</td>
                <td class="bold">{h_no}</td>
                <td class="bold horse-name">{name}</td>
                <td>{draw}</td>
                <td>{jockey}</td>
                <td class="odds">{odds}</td>
                <td class="prob">{m_pct}</td>
                <td class="edge">{edge}</td>
            </tr>
            """

    races_html += f"""
    <div class="race-card" id="race-{r_no}">
        <div class="race-header">
            <span>🏇 第 {r_no} 場</span>
            <span class="race-count">{h_count} 匹馬</span>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>名次</th><th>馬號</th><th style="text-align:left;padding-left:8px;">馬名</th><th>檔位</th><th>騎師</th><th>賠率</th><th>勝率</th><th>Edge</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>
    """

if not races_html:
    body_content = f"""
    <div class="fallback-card">
        <pre>{raw_text}</pre>
    </div>
    """
else:
    body_content = f"""
    <div class="section-title">🎫 實戰下注指南</div>
    {strat_cards_html}
    <div class="section-title" style="margin-top:20px;">📋 各場排位勝率榜</div>
    <div class="nav-bar">
        {nav_buttons}
    </div>
    {races_html}
    """

html_template = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🏇 香港賽馬量化指南 - {venue_text}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            background-color: #0b0b0e;
            color: #e5e5ea;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 12px 10px 40px 10px;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
        }}
        .header {{
            background: #18181c;
            padding: 14px 16px;
            border-radius: 14px;
            border-left: 4px solid #30d158;
            margin-bottom: 14px;
        }}
        h1 {{
            font-size: 1.15rem;
            margin: 0 0 6px 0;
            color: #ffffff;
            font-weight: 700;
        }}
        .status {{
            font-size: 0.8rem;
            color: #8e8e93;
            line-height: 1.5;
        }}
        .badge-hk {{
            display: inline-block;
            background: #ff3b30;
            color: #fff;
            padding: 2px 7px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 700;
        }}
        .badge-live {{
            display: inline-block;
            background: #30d158;
            color: #000;
            padding: 2px 7px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 700;
        }}
        .section-title {{
            font-size: 0.95rem;
            font-weight: 700;
            color: #ffffff;
            margin: 16px 0 10px 2px;
        }}
        .strategy-card {{
            background: #18181c;
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 10px;
            border: 1px solid #28282e;
        }}
        .strategy-title {{
            color: #ffd60a;
            font-weight: 700;
            font-size: 0.85rem;
            margin-bottom: 6px;
        }}
        .strategy-content {{
            margin: 0;
            font-family: ui-monospace, Menlo, Consolas, monospace;
            font-size: 0.75rem;
            line-height: 1.45;
            color: #d1d1d6;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .nav-bar {{
            display: flex;
            overflow-x: auto;
            gap: 8px;
            padding-bottom: 8px;
            margin-bottom: 12px;
            -webkit-overflow-scrolling: touch;
        }}
        .nav-btn {{
            flex: 0 0 auto;
            background: #202026;
            color: #30d158;
            text-decoration: none;
            font-weight: 700;
            font-size: 0.78rem;
            padding: 6px 12px;
            border-radius: 8px;
            border: 1px solid #2e2e38;
        }}
        .race-card {{
            background: #18181c;
            border-radius: 14px;
            margin-bottom: 16px;
            overflow: hidden;
            border: 1px solid #28282e;
        }}
        .race-header {{
            background: #202026;
            padding: 10px 14px;
            font-size: 0.92rem;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #28282e;
        }}
        .race-count {{
            font-size: 0.75rem;
            color: #8e8e93;
            font-weight: normal;
        }}
        .table-scroll {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
            white-space: nowrap;
            text-align: center;
        }}
        th {{
            background: #141417;
            color: #8e8e93;
            font-weight: 600;
            padding: 8px 7px;
            font-size: 0.72rem;
            border-bottom: 1px solid #28282e;
        }}
        td {{
            padding: 9px 7px;
            border-bottom: 1px solid #222228;
            color: #d1d1d6;
        }}
        .rank-badge {{
            display: inline-block;
            width: 20px;
            height: 20px;
            line-height: 20px;
            border-radius: 50%;
            font-weight: 700;
            font-size: 0.72rem;
        }}
        .rank-1 {{ background: #ffd60a; color: #000; }}
        .rank-2 {{ background: #aeaeb2; color: #000; }}
        .rank-3 {{ background: #ff9f0a; color: #000; }}
        .rank-other {{ background: #2c2c34; color: #8e8e93; }}
        .bold {{ font-weight: 700; color: #fff; }}
        .horse-name {{ text-align: left; padding-left: 8px; }}
        .odds {{ color: #64d2ff; }}
        .prob {{ color: #30d158; font-weight: 700; }}
        .edge {{ color: #ff375f; font-weight: 600; }}
        .fallback-card {{
            background: #18181c;
            padding: 12px;
            border-radius: 12px;
            overflow-x: auto;
        }}
        .fallback-card pre {{
            margin: 0;
            font-family: ui-monospace, Menlo, Consolas, monospace;
            font-size: 0.72rem;
            color: #30d158;
            white-space: pre;
            word-break: normal;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏇 香港賽馬量化實戰指南</h1>
            <div class="status">
                <span class="badge-hk">香港本地</span> <span class="badge-live">{venue_text}</span> 賽事日：<strong>{target_race_date}</strong><br>
                最後刷新時間：{hkt_now} (HKT)
            </div>
        </div>
        {body_content}
    </div>
</body>
</html>
"""

os.makedirs('public', exist_ok=True)
with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

print(
    f'✅ 成功生成【香港本地賽事 {target_race_date} {venue_text}】手機原生版網頁'
    ' public/index.html'
)