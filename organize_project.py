# -*- coding: utf-8 -*-
import os
import shutil
import subprocess

print("=" * 60)
print("🧹 開始執行專案檔案大掃除與模組化歸檔...")
print("=" * 60)

# 1. 建立歸檔資料夾
os.makedirs("archive_old_scripts", exist_ok=True)
os.makedirs("research_and_backtest", exist_ok=True)

# 2. 刪除無用檔案與衝突目錄
if os.path.exists("新增 PY 檔案.py"):
    os.remove("新增 PY 檔案.py")
    print("🗑️ 已刪除: 新增 PY 檔案.py")

if os.path.exists("public"):
    shutil.rmtree("public")
    print("🗑️ 已移除 public/ 目錄，徹底根除雙重路徑衝突")

# 3. 歸檔回測與模型訓練腳本
research_files = [
    "backtest_place_allup.py",
    "backtest_top3_box.py",
    "full_strategy_backtest.py",
    "train_and_backtest.py",
    "feature_engineering.py",
    "export_model.py",
    "check_db.py"
]

for f in research_files:
    if os.path.exists(f):
        shutil.move(f, os.path.join("research_and_backtest", f))
        print(f"📦 已歸檔至 research/: {f}")

# 4. 歸檔已被 engine.py 取代、會互相覆寫的舊腳本
obsolete_files = [
    "generate_html.py",
    "live_smart_betslip.py",
    "publish_dashboard.py",
    "quant_core.py",
    "update_results.py",
    "get_top_horses.py",
    "live_predictor.py",
    "verify_status.py"
]

for f in obsolete_files:
    if os.path.exists(f):
        shutil.move(f, os.path.join("archive_old_scripts", f))
        print(f"📦 已歸檔至 archive/: {f}")

print("=" * 60)
print("✅ 大掃除完成！根目錄結構已清爽乾淨。")

# 提交變更至 Git
subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", "refactor: clean root directory and archive obsolete scripts"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
print("🎉 清理狀態已推送到 GitHub！")
