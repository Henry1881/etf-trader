"""
ETF 报告自动下载脚本
====================
从 GitHub 仓库下载云端生成的报告到本地。
使用多重镜像源 + 重试机制，确保国内网络环境下也能稳定下载。

用法：
  python download_reports.py           # 下载最近 7 天的报告
  python download_reports.py 20260820   # 下载指定日期报告
"""
import sys
import os
import time
import urllib.request
import urllib.error
import socket
from datetime import datetime, timedelta

# 配置：GitHub 仓库信息
REPO = "henry1881/etf-trader"
BRANCH = "main"

# 多重镜像源（按国内访问稳定性排序）
# 1. jsdelivr CDN（国内访问最稳定）
# 2. GitHub Raw（原始源，有时超时）
# 3. GitHub API（带 base64 内容，最可靠但较慢）
MIRROR_SOURCES = [
    f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/reports/",
    f"https://raw.fastgit.org/{REPO}/{BRANCH}/reports/",
    f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/reports/",
]

# GitHub Contents API（备用，返回 base64 编码内容）
GITHUB_API_URL = f"https://api.github.com/repos/{REPO}/contents/reports/"

# 本地报告目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(SCRIPT_DIR, "reports")


def download_from_mirror(url: str, local_path: str, timeout: int = 15) -> bool:
    """从单个镜像源下载，返回是否成功"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if len(data) < 100:  # 内容太短，可能是错误页
                return False
            with open(local_path, "wb") as f:
                f.write(data)
            return True
    except Exception:
        return False


def download_from_api(date_str: str, local_path: str, timeout: int = 15) -> bool:
    """从 GitHub Contents API 下载（返回 base64 编码内容）"""
    import base64
    filename = f"daily_report_{date_str}.md"
    url = GITHUB_API_URL + filename
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            import json
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("encoding") == "base64" and data.get("content"):
                content = base64.b64decode(data["content"])
                with open(local_path, "wb") as f:
                    f.write(content)
                return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise  # 404 表示文件不存在，不需要重试
    return False


def download_report(date_str: str) -> bool:
    """从多个镜像源下载指定日期的报告，带重试"""
    filename = f"daily_report_{date_str}.md"
    local_path = os.path.join(REPORT_DIR, filename)

    print(f"  下载 {date_str}...", end=" ", flush=True)

    # 先检查本地是否已有此报告
    if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
        print(f"已存在 ({os.path.getsize(local_path)} bytes)")
        return True

    # 尝试每个镜像源（每个重试 2 次）
    for mirror_idx, base_url in enumerate(MIRROR_SOURCES):
        url = base_url + filename
        for attempt in range(2):
            if download_from_mirror(url, local_path, timeout=15):
                size = os.path.getsize(local_path)
                print(f"成功 ({size} bytes) [源{mirror_idx+1}]")
                return True
            time.sleep(1)

    # 所有镜像源失败，尝试 GitHub API
    try:
        if download_from_api(date_str, local_path, timeout=15):
            size = os.path.getsize(local_path)
            print(f"成功 ({size} bytes) [API]")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("未找到（可能非交易日或尚未生成）")
            return False

    print("失败（所有源均超时或不可用）")
    return False


def download_recent_reports(days: int = 7):
    """下载最近 N 天的报告"""
    os.makedirs(REPORT_DIR, exist_ok=True)

    today = datetime.now()
    downloaded = 0

    print(f"检查最近 {days} 天的报告...")
    print(f"仓库: {REPO}")
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

    # 找最新的本地报告
    latest_file = None
    for i in range(days):
        d = today - timedelta(days=i)
        f = os.path.join(REPORT_DIR, f"daily_report_{d.strftime('%Y%m%d')}.md")
        if os.path.exists(f):
            latest_file = f
            break

    if latest_file:
        print(f"最新报告: {latest_file}")
    else:
        print("未找到任何报告")

    return downloaded


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 下载指定日期
        os.makedirs(REPORT_DIR, exist_ok=True)
        download_report(sys.argv[1])
    else:
        # 下载最近 7 天（扩大范围，确保补全缺失的报告）
        download_recent_reports(7)
