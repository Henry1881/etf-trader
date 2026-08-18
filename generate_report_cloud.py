"""
ETF 每日报告 - 云端版（GitHub Actions 专用）
=============================================
数据源：akshare（东方财富 API），不依赖通达信 MCP
功能：在 GitHub Actions 云端环境中运行，生成报告并推送到仓库

用法：
  python generate_report_cloud.py              # 生成今日报告
  python generate_report_cloud.py 20260817     # 补生成指定日期
"""
import sys
import os

# 确保 src 在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# UTF-8 输出
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import time
import warnings
warnings.filterwarnings("ignore")

from datetime import datetime, timedelta
import akshare as ak
import pandas as pd

from src.indicators.technical_indicators import TechnicalIndicators
from src.signal_engine.signal_generator import SignalGenerator
from src.reporter.report_generator import ReportGenerator


ETF_CONFIG = {
    "588170": {"name": "科创半导体ETF华夏", "exchange": "sh"},
    "159611": {"name": "广发中证全指电力ETF", "exchange": "sz"},
    "159227": {"name": "华夏国证航天航空ETF", "exchange": "sz"},
    "159272": {"name": "机器人ETF富国", "exchange": "sz"},
    "159622": {"name": "创新药ETF沪港深", "exchange": "sz"},
}


def fetch_kline(symbol: str, count: int = 100) -> pd.DataFrame:
    """用 akshare 拉取真实日K线（带重试）"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=200)).strftime("%Y%m%d")

    for attempt in range(4):
        try:
            raw = ak.fund_etf_hist_em(
                symbol=symbol, period="daily",
                start_date=start_date, end_date=end_date, adjust=""
            )
            if raw is not None and not raw.empty:
                rename = {
                    "日期": "date", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low",
                    "成交量": "volume", "成交额": "amount"
                }
                df = raw.rename(columns=rename)
                df["date"] = pd.to_datetime(df["date"])
                for c in ["open", "high", "low", "close", "volume", "amount"]:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
                df = df.sort_values("date").reset_index(drop=True)
                cols = [c for c in ["date", "open", "high", "low", "close", "volume", "amount"]
                        if c in df.columns]
                df = df[cols]
                return df.tail(count).reset_index(drop=True)
        except Exception as e:
            print(f"  [{symbol}] 第{attempt+1}次失败: {type(e).__name__}: {e}")
            time.sleep(3 + attempt * 2)
    return pd.DataFrame()


def generate_report(target_date: str = None):
    now = datetime.now()
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 云端报告生成...")

    if target_date:
        target_ts = pd.Timestamp(target_date)
        print(f"  补生成模式: {target_ts.strftime('%Y-%m-%d')}")
    else:
        target_ts = None
        print(f"  正常模式: 今日报告")

    indicators = TechnicalIndicators()
    signal_generator = SignalGenerator()
    report_generator = ReportGenerator()

    etf_results = {}
    all_warnings = []

    for symbol, info in ETF_CONFIG.items():
        try:
            print(f"\n  处理 {symbol} ({info['name']})...")
            df = fetch_kline(symbol, count=100)
            if df.empty:
                all_warnings.append(f"{symbol}: akshare 获取失败")
                continue

            # 补生成模式：截取到目标日期
            if target_ts:
                df = df[df["date"] <= target_ts].reset_index(drop=True)
                print(f"    截取到 {target_date}: {len(df)} 行")
            else:
                print(f"    获取 {len(df)} 行 ({df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d')})")

            if len(df) < 20:
                all_warnings.append(f"{symbol}: 数据不足 {len(df)} 行")
                continue

            # 计算指标
            df_with = indicators.calculate_all(df)
            latest = indicators.get_latest_indicators(df_with)
            if not latest:
                last = df_with.iloc[-1]
                latest = {"price": {"close": last["close"], "open": last["open"],
                                     "high": last["high"], "low": last["low"],
                                     "volume": last["volume"]}}

            # 涨跌幅
            close = df["close"].iloc[-1]
            if len(df) > 1:
                prev_close = df["close"].iloc[-2]
                change = (close - prev_close) / prev_close * 100
            else:
                change = 0

            if "price" in latest and len(df) > 1:
                latest["price"]["prev_close"] = df["close"].iloc[-2]

            # 信号（数据质量=100，akshare 真实数据）
            signal = signal_generator.generate_signal(latest, data_quality=100)
            signal["current_price"] = close
            signal["price_change"] = round(change, 2)

            etf_results[symbol] = {
                "name": info["name"],
                "exchange": info["exchange"],
                "signal": signal,
                "data": df_with
            }

            conf = signal.get("confidence", 0)
            ma20 = latest.get("ma", {}).get("ma_20", 0)
            print(f"    完成: 信号={signal['final_signal']} 价={close:.4f} 涨跌={change:+.2f}% MA20={ma20:.4f} 置信度={conf:.1f}/10")

        except Exception as e:
            print(f"    错误: {e}")
            all_warnings.append(f"{symbol}: {e}")

    if etf_results:
        quality = max(50, 100 - len(all_warnings) * 15)
        data_meta = {
            "source": "akshare(东方财富API) - GitHub Actions 云端生成",
            "last_trade_date": list(etf_results.values())[0]["data"]["date"].iloc[-1].strftime("%Y-%m-%d"),
            "validated": True,
            "quality_score": quality,
            "warnings": ["云端生成，基于 akshare 真实日K线"] + all_warnings[:3]
        }
        report = report_generator.generate_daily_report(etf_results, data_meta)

        if target_date:
            filepath = report_generator.save_report(report, f"daily_report_{target_date}.md")
        else:
            filepath = report_generator.save_report(report)
        print(f"\n  报告已保存: {filepath}")
        print(f"  数据质量: {quality}/100")
    else:
        # 即使数据获取失败，也生成一个错误报告（方便排查）
        import os
        os.makedirs("reports", exist_ok=True)
        date_str = target_date or datetime.now().strftime("%Y%m%d")
        error_report = f"""# ETF每日分析报告

**分析日期**: {date_str}

## ⚠️ 数据获取失败

云端报告生成时无法获取 ETF 数据。

### 可能原因
1. akshare 在 GitHub Actions 服务器（美国）上无法访问东方财富 API
2. 网络超时
3. 非交易日（周末/节假日）

### 警告信息
"""
        for w in all_warnings:
            error_report += f"- {w}\n"
        error_report += f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n"

        filepath = os.path.join("reports", f"daily_report_{date_str}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(error_report)
        print(f"\n  错误报告已保存: {filepath}")
        print(f"  警告数: {len(all_warnings)}")

    # 调试：列出 reports/ 目录内容
    print("\n  === reports/ 目录内容 ===")
    import subprocess
    result = subprocess.run(["ls", "-la", "reports/"], capture_output=True, text=True)
    print(result.stdout or result.stderr or "  (空)")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_report(target_date=date_arg)
