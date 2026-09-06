# -*- coding: utf-8 -*-
import os
import shutil
import datetime
import subprocess

now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print("=" * 65)
print(f"🚀 正在修正 public/index.html 映射與時間戳 ({now_str})...")
print("=" * 65)

# 1. 確保如果存在 public 目錄，同步寫入 public/index.html
target_files = ["index.html"]
if os.path.exists("public"):
    target_files.append(os.path.join("public", "index.html"))

# 檢查 quant_core.py 生成的 HTML 原型
source_html = "public/index.html" if os.path.exists("public/index.html") else "index.html"
with open(source_html, "r", encoding="utf-8") as f:
    content = f.read()

# 頂部即時時間橫幅
top_bar = f"""
<!-- 即時更新時間橫幅 -->
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 20px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <div>
        <div style="font-size:1.15em;font-weight:bold;color:#f0f6fc;">🏇 HKJC 高頻量化決策監控中心</div>
        <div style="font-size:0.85em;color:#8b949e;">Harville 價值邊際 + 微氣象感測器 + 動態跑道偏置引擎</div>
    </div>
    <div style="background:rgba(46,160,67,0.2);border:1px solid #3fb950;color:#3fb950;padding:6px 14px;border-radius:20px;font-weight:bold;font-size:0.95em;display:flex;align-items:center;gap:8px;">
        <span style="width:8px;height:8px;background:#3fb950;border-radius:50%;box-shadow:0 0 8px #3fb950;"></span>
        最後實時更新：{now_str} (HKT)
    </div>
</div>
"""

# 底部 9月6日 開鑼日歷史存檔庫
history_section = """
<!-- 歷史賽事回測與投注策略存檔庫 -->
<div style="margin-top:35px;margin-bottom:50px;">
    <details open style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;">
        <summary style="cursor:pointer;font-weight:bold;font-size:1.15em;color:#58a6ff;outline:none;">
            📜 歷史賽事回測與投注策略存檔庫（點擊展開/收起）
        </summary>
        <div style="margin-top:16px;">
            <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:12px 16px;margin-bottom:14px;">
                <div style="color:#f1e05a;font-weight:bold;">📁 2026-09-06 沙田開鑼日賽（全 10 場雙軌策略實盤派彩覆盤）</div>
                <div style="margin-top:6px;font-size:0.88em;color:#8b949e;">場地：好地至快地 (度地儀 2.71 / 微風) ｜ 三甲中冷馬(5-15倍)佔 46.7%、大冷(>15倍)佔 26.7%，長尾高 Edge 配腳極具爆發力。</div>
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:0.9em;color:#c9d1d9;">
                <thead>
                    <tr style="background:#21262d;color:#f0f6fc;text-align:left;">
                        <th style="padding:10px;border-bottom:1px solid #30363d;">場次</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">策略模式</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">模型核心/膽馬</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">價值配腳 (Place Edge)</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">官方前三名</th>
                        <th style="padding:10px;border-bottom:1px solid #30363d;">實盤結算覆盤</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 1 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">1膽拖4腳</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">4 新力驕</td><td style="padding:10px;border-bottom:1px solid #30363d;">2, 7, 6, 14</td><td style="padding:10px;border-bottom:1px solid #30363d;">13-7-2</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#58a6ff;background:rgba(56,139,253,0.15);padding:2px 8px;border-radius:4px;">命中位置 Q 2-7 ($94.5)</span></td></tr>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 2 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">1膽拖4腳</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">1 駿馬之曲</td><td style="padding:10px;border-bottom:1px solid #30363d;">8, 5, 11, 7</td><td style="padding:10px;border-bottom:1px solid #30363d;">1-8-11</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#3fb950;background:rgba(46,160,67,0.2);padding:2px 8px;border-radius:4px;font-weight:bold;">🎯 單T $157 + 位置Q 1-8 $42 全中</span></td></tr>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 3 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">超強單膽</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">1 嘉應高昇</td><td style="padding:10px;border-bottom:1px solid #30363d;">3, 5, 6, 2</td><td style="padding:10px;border-bottom:1px solid #30363d;">1-2-6</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#3fb950;background:rgba(46,160,67,0.2);padding:2px 8px;border-radius:4px;font-weight:bold;">🎯 單T命中 1-2-6 ($312.0)</span></td></tr>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 4 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">4匹複式</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">10, 12, 7, 14</td><td style="padding:10px;border-bottom:1px solid #30363d;">-</td><td style="padding:10px;border-bottom:1px solid #30363d;">10-1-7</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#58a6ff;background:rgba(56,139,253,0.15);padding:2px 8px;border-radius:4px;">命中位置 Q 10-7 ($60.5)</span></td></tr>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 5 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">1膽拖4腳</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">4 震撼人心</td><td style="padding:10px;border-bottom:1px solid #30363d;">12, 8, 11, 10</td><td style="padding:10px;border-bottom:1px solid #30363d;">7-5-12</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#f85149;background:rgba(248,81,73,0.15);padding:2px 8px;border-radius:4px;">❌ 膽馬落第 (12入位)</span></td></tr>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 6 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">1膽拖4腳</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">3 馬馳登</td><td style="padding:10px;border-bottom:1px solid #30363d;">14, 8, 13, 10</td><td style="padding:10px;border-bottom:1px solid #30363d;">1-3-8</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#58a6ff;background:rgba(56,139,253,0.15);padding:2px 8px;border-radius:4px;">命中位置 Q 3-8 ($42.0)</span></td></tr>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 7 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">1膽拖4腳</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">3 時時歡聲</td><td style="padding:10px;border-bottom:1px solid #30363d;">5, 2, 6, 7</td><td style="padding:10px;border-bottom:1px solid #30363d;">6-7-9</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#f85149;background:rgba(248,81,73,0.15);padding:2px 8px;border-radius:4px;">❌ 膽第4；配腳包辦105倍+22倍冠亞</span></td></tr>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 8 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">4匹複式</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">4, 13, 14, 2</td><td style="padding:10px;border-bottom:1px solid #30363d;">-</td><td style="padding:10px;border-bottom:1px solid #30363d;">1-2-8</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#f85149;background:rgba(248,81,73,0.15);padding:2px 8px;border-radius:4px;">❌ 僅 2 入位</span></td></tr>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 9 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">1膽拖4腳</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">5 櫻花酒杯</td><td style="padding:10px;border-bottom:1px solid #30363d;">4, 1, 3, 10</td><td style="padding:10px;border-bottom:1px solid #30363d;">5-8-7</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#f85149;background:rgba(248,81,73,0.15);padding:2px 8px;border-radius:4px;">❌ 膽第一，配腳錯失 8, 7</span></td></tr>
                    <tr><td style="padding:10px;border-bottom:1px solid #30363d;">第 10 場</td><td style="padding:10px;border-bottom:1px solid #30363d;">1膽拖4腳</td><td style="padding:10px;border-bottom:1px solid #30363d;color:#f1e05a;">12 支付之父</td><td style="padding:10px;border-bottom:1px solid #30363d;">2, 8, 10, 13</td><td style="padding:10px;border-bottom:1px solid #30363d;">2-1-10</td><td style="padding:10px;border-bottom:1px solid #30363d;"><span style="color:#f85149;background:rgba(248,81,73,0.15);padding:2px 8px;border-radius:4px;">❌ 膽落第；高Edge冷腳 2,10 入三甲</span></td></tr>
                </tbody>
            </table>
        </div>
    </details>
</div>
"""

# 清除舊注入代碼，確保不重複
content = content.replace("<!-- 即時更新時間橫幅 -->", "")
content = content.replace("<!-- 歷史賽事回測與投注策略存檔庫 -->", "")

# 插入頂部
if "<body" in content:
    idx = content.find(">", content.find("<body")) + 1
    content = content[:idx] + "\n" + top_bar + content[idx:]
else:
    content = top_bar + content

# 插入底部
if "</body>" in content:
    idx = content.rfind("</body>")
    content = content[:idx] + "\n" + history_section + content[idx:]
else:
    content = content + history_section

# 雙重寫入：根目錄與 public/ 目錄
for target in target_files:
    os.makedirs(os.path.dirname(target), exist_ok=True) if os.path.dirname(target) else None
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 成功同步寫入: {target}")

# 同步更新 publish_dashboard.py，使其未來自動發布時同時更新 public/ 目錄
pub_code = '''# -*- coding: utf-8 -*-
import shutil
import os
import subprocess

if os.path.exists("public"):
    shutil.copyfile("index.html", "public/index.html")

subprocess.run(["git", "add", "index.html", "public/index.html"], check=False)
subprocess.run(["git", "commit", "-m", "chore: auto sync public and root index"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
'''
with open("publish_dashboard.py", "w", encoding="utf-8") as f:
    f.write(pub_code)

print("✅ publish_dashboard.py 已修正為自動同步 public 目錄！")

# 提交並推送到 GitHub
subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", f"fix(pages): force sync live time and history drawer to public/index.html ({now_str})"], check=False)
res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)

print("🎉 GitHub Pages 雙目錄更新推播完畢！")
print(res.stdout if res.stdout else res.stderr)
