# ETF每日报告后台守护进程
# 放在启动文件夹，登录后自动运行，使用schedule库定时执行

param(
    [int]$ReportHour = 20,
    [int]$ReportMinute = 0
)

# Set encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Project paths
$UserProfile = $env:USERPROFILE
$ProjectDir = Join-Path $UserProfile "Documents\trae_projects\EtF Trader"
$PythonPath = Join-Path $UserProfile "python-sdk\python3.13.2\python.exe"
$ScriptPath = Join-Path $ProjectDir "generate_report_v3.py"
$LogDir = Join-Path $ProjectDir "logs"

# Import schedule module via Python
$ScheduleScript = @"
import schedule
import time
import subprocess
import os
import sys
from datetime import datetime

PROJECT_DIR = r"$ProjectDir"
PYTHON_PATH = r"$PythonPath"
SCRIPT_PATH = r"$ScriptPath"
LOG_DIR = r"$LogDir"

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def generate_report():
    now = datetime.now()
    log_file = os.path.join(LOG_DIR, f"daemon_{now.strftime('%Y%m%d')}.log")
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] [START] Report generation started\n")
    
    try:
        # Run the report generation script
        result = subprocess.run(
            [PYTHON_PATH, SCRIPT_PATH],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Output:\n{result.stdout}\n")
            if result.stderr:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error:\n{result.stderr}\n")
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Exit code: {result.returncode}\n")
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [END] Report generation finished\n\n")
        
        if result.returncode == 0:
            print(f"[SUCCESS] Report generated at {datetime.now()}")
        else:
            print(f"[ERROR] Report generation failed with exit code {result.returncode}")
            
    except Exception as e:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Exception: {e}\n\n")
        print(f"[ERROR] Exception: {e}")

# Schedule the task for weekdays at 20:00
# Using Python's built-in scheduler
schedule.every().monday.at("20:00").do(generate_report)
schedule.every().tuesday.at("20:00").do(generate_report)
schedule.every().wednesday.at("20:00").do(generate_report)
schedule.every().thursday.at("20:00").do(generate_report)
schedule.every().friday.at("20:00").do(generate_report)

print(f"ETF Report Daemon Started at {datetime.now()}")
print(f"Scheduled: Every weekday at 20:00")
print(f"Working directory: {PROJECT_DIR}")
print(f"Log directory: {LOG_DIR}")

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(30)  # Check every 30 seconds
"@

# Write the Python scheduler script
$ScheduleScriptPath = Join-Path $ProjectDir "etf_daemon.py"
$ScheduleScript | Out-File -FilePath $ScheduleScriptPath -Encoding UTF8

# Run the daemon
Write-Host "Starting ETF Report Daemon..."
Write-Host "Press Ctrl+C to stop"

& $PythonPath $ScheduleScriptPath
