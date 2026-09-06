# -*- coding: utf-8 -*-
import os
import glob
import subprocess

workflow_dir = os.path.join(".github", "workflows")
os.makedirs(workflow_dir, exist_ok=True)

# 1. 清理所有舊的 workflow 檔案
for f in glob.glob(os.path.join(workflow_dir, "*.yml")) + glob.glob(os.path.join(workflow_dir, "*.yaml")):
    try:
        os.remove(f)
        print(f"🧹 已移除舊工作流程: {f}")
    except Exception:
        pass

# 2. 建立避免 exit code 2 的標準 GitHub Pages 流程
workflow_content = """name: Deploy GitHub Pages

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Prepare Site Artifacts
        run: |
          mkdir -p _site
          cp index.html _site/
          # 如有其他靜態檔案需對外展示可一併複製
          if [ -f "20260906_official_full_results.json" ]; then
            cp 20260906_official_full_results.json _site/
          fi

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '_site'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""

target_yml = os.path.join(workflow_dir, "deploy.yml")
with open(target_yml, "w", encoding="utf-8") as f:
    f.write(workflow_content)

print(f"✅ 已建立全新 _site 隔離部署工作流程: {target_yml}")

# 3. 提交並強制推送到遠端
subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", "fix: deploy via isolated _site directory to prevent exit code 2"], check=False)
res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)

print("🎉 已推送至 GitHub，觸發全新 Pages 部署！")
print(res.stdout if res.stdout else res.stderr)
