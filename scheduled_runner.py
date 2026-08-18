"""
ETF 每日报告 - 任务计划程序入口 (scheduled_runner.py)
被 Windows 任务计划程序调用，运行报告生成并把完整输出写入日志。
比 .bat 更可靠：不依赖 wmic（Win11 已移除），跨版本兼容。
"""
import subprocess
import sys
import os
from datetime import datetime

PROJECT = os.path.dirname(os.path.abspath(__file__))
PYTHON = r"C:\Users\清朗\python-sdk\python3.13.2\python.exe"
SCRIPT = os.path.join(PROJECT, "generate_report_v3.py")
LOG_DIR = os.path.join(PROJECT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

today = datetime.now().strftime("%Y%m%d")
log_file = os.path.join(LOG_DIR, f"scheduled_{today}.log")

# 关键：为子进程启用 Python UTF-8 模式，避免 GBK 编码下 emoji 输出崩溃
child_env = os.environ.copy()
child_env["PYTHONUTF8"] = "1"
child_env["PYTHONIOENCODING"] = "utf-8"

with open(log_file, "a", encoding="utf-8") as f:
    f.write("\n" + "=" * 60 + "\n")
    f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] === Scheduled report START ===\n")
    f.write(f"Python: {PYTHON}\n")
    f.write(f"Script: {SCRIPT}\n")
    f.write(f"PYTHONUTF8=1, PYTHONIOENCODING=utf-8\n")
    f.write("=" * 60 + "\n")
    f.flush()
    try:
        result = subprocess.run(
            [PYTHON, SCRIPT],
            cwd=PROJECT,
            stdout=f,
            stderr=subprocess.STDOUT,
            env=child_env,
            timeout=600,
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] ERROR: 超时 (>600s)\n")
        exit_code = 124
    except Exception as e:
        f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] ERROR: {e}\n")
        exit_code = 1
    f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] === END (exit {exit_code}) ===\n")

sys.exit(exit_code)
