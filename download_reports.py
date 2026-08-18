"""
ETF 报告自动下载脚本
====================
从 GitHub 仓库下载云端生成的报告到本地。
不需要安装 git，用 Python requests 直接从 GitHub Raw URL 下载。

用法：
  python download_reports.py           # 下载最近的报告
  python download_reports.py 20260817   # 下载指定日期报告
"""
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# 配置：注册 GitHub 后填入你的仓库信息
# 格式：https://raw.githubusercontent.com/{用户名}/{仓库名}/{分支}/
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/USER/REPO/main/"

# 本地报告目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(SCRIPT_DIR, "reports")


def download_report(date_str: str) -> bool:
    """从 GitHub 下载指定日期的报告"""
    filename = f"daily_report_{date_str}.md"
    url = GITHUB_RAW_BASE + f"reports/{filename}"
    local_path = os.path.join(REPORT_DIR, filename)

    try:
        print(f"  下载 {date_str}...", end=" ")
        urllib.request.urlretrieve(url, local_path)
        size = os.path.getsize(local_path)
        print(f"成功 ({size} bytes)")
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("未找到（可能非交易日或尚未生成）")
        else:
            print(f"HTTP 错误 {e.code}")
        return False
    except Exception as e:
        print(f"失败: {e}")
        return False


def download_recent_reports(days: int = 5):
    """下载最近 N 天的报告"""
    os.makedirs(REPORT_DIR, exist_ok=True)

    today = datetime.now()
    downloaded = 0

    print(f"检查最近 {days} 天的报告...")
    print(f"数据源: {GITHUB_RAW_BASE}")
    print()

    for i in range(days):
        d = today - timedelta(days=i)
        # 跳过周末
        if d.weekday() >= 5:
            continue
        date_str = d.strftime("%Y%m%d")
        if download_report(date_str):
            downloaded += 1

    print(f"\n完成: 下载了 {downloaded} 份报告")
    if downloaded > 0:
        latest_file = os.path.join(REPORT_DIR, f"daily_report_{today.strftime('%Y%m%d')}.md")
        if not os.path.exists(latest_file):
            # 找最新的
            for i in range(days):
                d = today - timedelta(days=i)
                f = os.path.join(REPORT_DIR, f"daily_report_{d.strftime('%Y%m%d')}.md")
                if os.path.exists(f):
                    latest_file = f
                    break
        print(f"最新报告: {latest_file}")
    return downloaded


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 下载指定日期
        os.makedirs(REPORT_DIR, exist_ok=True)
        download_report(sys.argv[1])
    else:
        # 下载最近 5 天
        download_recent_reports(5)
