import subprocess, sys
res = subprocess.run([sys.executable, "live_smart_betslip.py"], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)
