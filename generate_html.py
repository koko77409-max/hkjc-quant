from datetime import datetime, timezone, timedelta
import io
import os
import sys
from live_smart_betslip import get_upcoming_local_race, run_smart_betslip

# 1. 自動鎖定「香港本地」下一個賽馬日
target_race_date, target_venue = get_upcoming_local_race()
venue_text = '沙田 (ST)' if target_venue == 'ST' else '跑馬地 (HV)'
print(f'🏇 成功鎖定香港本地賽事: {target_race_date} {venue_text}')

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

# 打印到終端機以供監控核對
print(raw_text)

# 驗證輸出是否包含賽事數據
if '未能抓取' in raw_text or '共 0 匹馬' in raw_text or not raw_text.strip():
    print(f'❌ 生成失敗：未能獲取 {target_race_date} 之有效賽事資料。')
    sys.exit(1)

# 香港時間 (UTC+8)
hkt_now = datetime.now(timezone(timedelta(hours=8))).strftime(
    '%Y-%m-%d %H:%M:%S'
)

# 3. 封裝為深色模式手機響應式 HTML
html_template = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🏇 香港賽馬量化指南 - {venue_text}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            background-color: #121212;
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 10px;
        }}
        .container {{
            max-width: 680px;
            margin: 0 auto;
        }}
        .header {{
            background: #1e1e1e;
            padding: 14px 16px;
            border-radius: 12px;
            border-left: 4px solid #00e676;
            margin-bottom: 12px;
        }}
        h1 {{
            font-size: 1.15rem;
            margin: 0 0 6px 0;
            color: #ffffff;
        }}
        .status {{
            font-size: 0.8rem;
            color: #aaa;
            line-height: 1.4;
        }}
        .badge-hk {{
            display: inline-block;
            background: #d32f2f;
            color: #fff;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: bold;
            margin-right: 4px;
        }}
        .badge-live {{
            display: inline-block;
            background: #2e7d32;
            color: #fff;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: bold;
            margin-right: 4px;
        }}
        pre {{
            background: #1a1a1a;
            padding: 12px;
            border-radius: 12px;
            overflow-x: auto;
            font-family: ui-monospace, Menlo, Consolas, "Courier New", monospace;
            font-size: 0.75rem;
            line-height: 1.42;
            color: #00e676;
            white-space: pre-wrap;
            word-break: break-word;
            border: 1px solid #2a2a2a;
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
        <pre>{raw_text}</pre>
    </div>
</body>
</html>
"""

os.makedirs('public', exist_ok=True)
with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

print(
    f'✅ 成功生成【香港本地賽事 {target_race_date} {venue_text}】手機網頁'
    ' public/index.html'
)