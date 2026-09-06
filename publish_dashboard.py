# -*- coding: utf-8 -*-
import shutil
import os
import subprocess

# 確保根目錄與 public 目錄完全同步
if os.path.exists("public") and os.path.exists("public/index.html"):
    shutil.copyfile("public/index.html", "index.html")

subprocess.run(["git", "add", "index.html", "public/index.html", "20260906_official_full_results.json"], check=False)
subprocess.run(["git", "commit", "-m", "chore: sync validated dashboard state"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
