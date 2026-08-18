"""
ETF每日报告守护进程
- 每个工作日（周一至周五）20:00自动生成报告
- 可设置开机自启动（放入 Windows 启动文件夹）
- 支持后台运行
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime, timedelta

# 配置
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_PATH = r"C:\Users\清朗\python-sdk\python3.13.2\python.exe"
SCRIPT_PATH = os.path.join(PROJECT_DIR, "generate_report_v3.py")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
REPORT_DIR = os.path.join(PROJECT_DIR, "reports")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# 全局状态
running = True
last_report_date = None

def log(message, level="INFO"):
    """写入日志"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    log_file = os.path.join(LOG_DIR, f"daemon_{date_str}.log")
    
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry + "\n")
    
    print(log_entry)

def generate_report():
    """生成ETF日报告"""
    global last_report_date
    
    log("Starting report generation...", "INFO")
    
    try:
        # 运行报告生成脚本
        result = subprocess.run(
            [PYTHON_PATH, SCRIPT_PATH],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            # 检查报告文件
            today = datetime.now().strftime("%Y%m%d")
            report_file = os.path.join(REPORT_DIR, f"daily_report_{today}.md")
            
            if os.path.exists(report_file):
                file_size = os.path.getsize(report_file)
                log(f"Report generated: {report_file} (size: {file_size} bytes)", "SUCCESS")
                last_report_date = today
            else:
                log(f"WARNING: Report file not found: {report_file}", "WARNING")
        else:
            log(f"Report generation failed (exit code: {result.returncode})", "ERROR")
            if result.stderr:
                log(f"Error: {result.stderr[:500]}", "ERROR")
                
    except subprocess.TimeoutExpired:
        log("Report generation timed out (5 minutes)", "ERROR")
    except Exception as e:
        log(f"Exception during report generation: {str(e)}", "ERROR")

def is_workday():
    """检查是否为工作日（周一至周五）"""
    today = datetime.now()
    return today.weekday() < 5  # 0=Monday, 4=Friday

def should_generate_report():
    """检查是否应该生成报告"""
    global last_report_date
    
    now = datetime.now()
    today = now.strftime("%Y%m%d")
    
    # 检查是否已经生成过今日报告
    if last_report_date == today:
        return False
    
    # 检查报告文件是否已存在
    report_file = os.path.join(REPORT_DIR, f"daily_report_{today}.md")
    if os.path.exists(report_file) and os.path.getsize(report_file) > 1000:
        last_report_date = today
        log(f"Report already exists for {today}", "INFO")
        return False
    
    # 必须是工作日
    if not is_workday():
        return False
    
    # 必须在目标时间之后（20:00）
    target_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
    return now >= target_time

def run_daemon():
    """运行守护进程"""
    global running
    
    log("=" * 50, "INFO")
    log("ETF Report Daemon Started", "START")
    log(f"Project directory: {PROJECT_DIR}", "INFO")
    log(f"Python path: {PYTHON_PATH}", "INFO")
    log(f"Script path: {SCRIPT_PATH}", "INFO")
    log(f"Report schedule: Every workday at 20:00", "INFO")
    log("=" * 50, "INFO")
    
    # 启动时立即检查是否需要生成报告
    if should_generate_report():
        log("Starting immediate report generation (startup check)...", "INFO")
        generate_report()
    
    log("Daemon is running. Checking every 60 seconds...", "INFO")
    log("Press Ctrl+C to stop.", "INFO")
    
    try:
        while running:
            # 每60秒检查一次
            time.sleep(60)
            
            # 检查是否应该生成报告
            if should_generate_report():
                generate_report()
                
    except KeyboardInterrupt:
        log("Daemon stopped by user.", "INFO")
    except Exception as e:
        log(f"Daemon exception: {str(e)}", "ERROR")
    finally:
        log("ETF Report Daemon Stopped", "STOP")

def manual_generate():
    """手动触发报告生成"""
    log("Manual report generation triggered.", "INFO")
    generate_report()

def check_status():
    """检查守护进程状态"""
    today = datetime.now().strftime("%Y%m%d")
    report_file = os.path.join(REPORT_DIR, f"daily_report_{today}.md")
    log_file = os.path.join(LOG_DIR, f"daemon_{today}.log")
    
    print("\n" + "=" * 50)
    print("ETF Report Status Check")
    print("=" * 50)
    print(f"Date: {today}")
    print(f"Workday: {is_workday()}")
    
    if os.path.exists(report_file):
        size = os.path.getsize(report_file)
        mtime = os.path.getmtime(report_file)
        mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"Report: {report_file}")
        print(f"  Size: {size} bytes")
        print(f"  Modified: {mtime_str}")
    else:
        print(f"Report: NOT FOUND")
    
    if os.path.exists(log_file):
        size = os.path.getsize(log_file)
        print(f"Log: {log_file}")
        print(f"  Size: {size} bytes")
        print("\nRecent log entries:")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(f"  {line.rstrip()}")
    else:
        print(f"Log: NOT FOUND")
    
    print("=" * 50 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ETF Report Daemon")
    parser.add_argument("--generate", "-g", action="store_true", 
                       help="Manually generate report")
    parser.add_argument("--status", "-s", action="store_true",
                       help="Check report status")
    parser.add_argument("--daemon", "-d", action="store_true",
                       help="Run as daemon (default)")
    
    args = parser.parse_args()
    
    if args.status:
        check_status()
    elif args.generate:
        manual_generate()
    else:
        run_daemon()
