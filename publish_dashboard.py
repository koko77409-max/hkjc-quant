# -*- coding: utf-8 -*-
import shutil
import os
import subprocess

if os.path.exists("public"):
    shutil.copyfile("index.html", "public/index.html")

subprocess.run(["git", "add", "index.html", "public/index.html"], check=False)
subprocess.run(["git", "commit", "-m", "chore: auto sync public and root index"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=False)
