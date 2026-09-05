import subprocess, sys, os

my_env = os.environ.copy()
my_env["PYTHONIOENCODING"] = "utf-8"

res = subprocess.run(
    [sys.executable, "live_smart_betslip.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=my_env
)

if res.stdout:
    print(res.stdout)
if res.stderr:
    print(res.stderr)
