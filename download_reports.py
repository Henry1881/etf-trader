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


def get_fallback_target_date() -> str:
    """计算兜底补生成的目标日期：
    - 周一早上开机（<12点）：上周五（昨日是周末）
    - 周六/周日开机：上周五
    - 工作日早上（<12点）：昨日（昨日是工作日）
    - 工作日晚上（>=12点）：今日（今日已收盘）
    """
    now = datetime.now()
    today = now.date()
    wd = today.weekday()  # 0=周一, 6=周日

    if wd == 5:  # 周六
        target = today - timedelta(days=1)      # 上周五
    elif wd == 6:  # 周日
        target = today - timedelta(days=2)      # 上周五
    elif wd == 0 and now.hour < 12:  # 周一早上
        target = today - timedelta(days=3)      # 上周五
    elif now.hour < 12:  # 工作日早上
        target = today - timedelta(days=1)      # 昨日
    else:                # 工作日晚上
        target = today                          # 今日

    return target.strftime("%Y%m%d")


def local_fallback_generate(date_str: str) -> bool:
    """本地兜底生成：调用 generate_report_cloud.py 生成指定日期报告"""
    gen_script = os.path.join(SCRIPT_DIR, "generate_report_cloud.py")
    if not os.path.exists(gen_script):
        print(f"  兜底脚本不存在: {gen_script}")
        return False

    print(f"\n=== 启动本地兜底生成: {date_str} ===")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, gen_script, date_str],
            cwd=SCRIPT_DIR,
            timeout=600,  # 最多 10 分钟
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"  [stderr]: {result.stderr}")

        # 检查是否生成成功
        local_path = os.path.join(REPORT_DIR, f"daily_report_{date_str}.md")
        if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
            size = os.path.getsize(local_path)
            print(f"  ✅ 兜底生成成功: {local_path} ({size} bytes)")
            return True
        else:
            print(f"  ❌ 兜底生成失败: 报告未生成或过小")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ❌ 兜底生成超时（>10分钟）")
        return False
    except Exception as e:
        print(f"  ❌ 兜底生成异常: {type(e).__name__}: {e}")
        return False


def ensure_latest_report():
    """兜底机制：确保目标日期报告存在，不存在则本地补跑。
    这是云端 cron 9次冗余触发都漏跑时的"最后防线"。"""
    target_date = get_fallback_target_date()
    target_file = os.path.join(REPORT_DIR, f"daily_report_{target_date}.md")

    if os.path.exists(target_file) and os.path.getsize(target_file) > 1000:
        print(f"\n兜底检查: {target_date} 报告已存在 "
              f"({os.path.getsize(target_file)} bytes)，无需补跑")
        return

    print(f"\n兜底检查: {target_date} 报告缺失，启动本地补跑...")
    local_fallback_generate(target_date)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 下载指定日期
        os.makedirs(REPORT_DIR, exist_ok=True)
        download_report(sys.argv[1])
    else:
        # 下载最近 7 天
        download_recent_reports(7)
        # 兜底机制：若目标日期报告缺失，本地补跑
        ensure_latest_report()
