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


def apply_forward_adjust(df: pd.DataFrame) -> pd.DataFrame:
    """对未复权数据做前复权处理（检测除权除息日并调整历史价格）"""
    if df.empty or len(df) < 2:
        return df

    price_cols = ["open", "high", "low", "close"]
    df = df.sort_values("date").reset_index(drop=True).copy()

    # 检测除权日：当天开盘价与前一天收盘价差异超过 20%
    adjust_factors = [1.0]  # 最新一天不需要调整
    for i in range(1, len(df)):
        prev_close = df.iloc[i - 1]["close"]
        curr_open = df.iloc[i]["open"]
        if prev_close > 0 and abs(curr_open / prev_close - 1) > 0.20:
            # 除权因子 = 当天开盘价 / 前一天收盘价
            factor = curr_open / prev_close
            print(f"    检测到除权日 {df.iloc[i]['date'].strftime('%Y-%m-%d')}: "
                  f"前收={prev_close:.4f}, 今开={curr_open:.4f}, 因子={factor:.4f}")
            adjust_factors.append(factor)
        else:
            adjust_factors.append(1.0)

    # 从最新一天往前累积复权因子
    # 如果有多天除权，需要累积
    cumulative = [1.0] * len(df)
    cum_factor = 1.0
    for i in range(len(df) - 1, -1, -1):
        cum_factor *= adjust_factors[i]
        cumulative[i] = cum_factor

    # 应用复权因子
    for j, col in enumerate(price_cols):
        if col in df.columns:
            df[col] = df[col] * cumulative

    return df


def fetch_kline(symbol: str, exchange: str, count: int = 100,
                 expected_date: pd.Timestamp = None) -> pd.DataFrame:
    """用 akshare 拉取真实日K线（带重试和数据时效性校验）
    优先新浪数据源，东方财富备选
    新浪数据源返回未复权数据，需手动做前复权处理

    关键改进：检查最后一行日期是否与 expected_date 一致
    若不一致说明数据源未刷新当天数据，重试或切换备用源
    """
    sina_symbol = f"{exchange}{symbol}"  # 如 sh588170, sz159611
    max_attempts = 6  # 增加重试次数，给数据源更多时间刷新

    for attempt in range(max_attempts):
        # 优先用新浪数据源（国内访问更稳定）
        try:
            raw = ak.fund_etf_hist_sina(symbol=sina_symbol)
            if raw is not None and not raw.empty:
                df = raw.copy()
                df["date"] = pd.to_datetime(df["date"])
                for c in ["open", "high", "low", "close", "volume", "amount"]:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
                df = df.sort_values("date").reset_index(drop=True)
                cols = [c for c in ["date", "open", "high", "low", "close", "volume", "amount"]
                        if c in df.columns]
                df = df[cols]

                # 前复权处理（新浪数据源返回未复权数据）
                df = apply_forward_adjust(df)

                # === 数据时效性校验 ===
                if expected_date is not None and not df.empty:
                    last_date = df["date"].iloc[-1]
                    if last_date.date() != expected_date.date():
                        print(f"  [{symbol}] 时效校验失败: 期望 {expected_date.strftime('%Y-%m-%d')}, "
                              f"实际最后日期 {last_date.strftime('%Y-%m-%d')} (第{attempt+1}次)")
                        # 数据未刷新，等待重试
                        if attempt < max_attempts - 1:
                            time.sleep(15 + attempt * 5)  # 逐步增加等待时间
                            continue
                        else:
                            print(f"  [{symbol}] 警告: 数据源未刷新，将使用最新可用数据")
                    else:
                        print(f"  [{symbol}] 时效校验通过: 最后一行 {last_date.strftime('%Y-%m-%d')}")
                return df.tail(count).reset_index(drop=True)
        except Exception as e:
            print(f"  [{symbol}] 新浪第{attempt+1}次失败: {type(e).__name__}")

        # 备选：东方财富（用前复权）
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=200)).strftime("%Y%m%d")
            raw = ak.fund_etf_hist_em(
                symbol=symbol, period="daily",
                start_date=start_date, end_date=end_date, adjust="qfq"
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
                # === 数据时效性校验 ===
                if expected_date is not None and not df.empty:
                    last_date = df["date"].iloc[-1]
                    if last_date.date() != expected_date.date():
                        print(f"  [{symbol}] 东方财富时效校验失败: 期望 {expected_date.strftime('%Y-%m-%d')}, "
                              f"实际 {last_date.strftime('%Y-%m-%d')}")
                        if attempt < max_attempts - 1:
                            time.sleep(15 + attempt * 5)
                            continue
                        else:
                            print(f"  [{symbol}] 警告: 东方财富数据源未刷新")
                    else:
                        print(f"  [{symbol}] 东方财富时效校验通过")
                return df.tail(count).reset_index(drop=True)
        except Exception as e:
            print(f"  [{symbol}] 东方财富第{attempt+1}次失败: {type(e).__name__}")

        time.sleep(5 + attempt * 3)
    return pd.DataFrame()


def report_already_ready(date_str: str) -> bool:
    """门禁检查：指定日期的报告是否已经生成且数据合格（非"数据未就绪"错误报告）。
    冗余 cron 触发时，若今天报告已存在且合格，直接跳过避免重复计算。"""
    filepath = os.path.join("reports", f"daily_report_{date_str}.md")
    if not os.path.exists(filepath):
        return False
    size = os.path.getsize(filepath)
    if size < 1000:
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            head = f.read(500)
        # "数据未就绪" 标题说明上次触发时数据源未刷新，需要重试
        if "数据未就绪" in head or "⚠️ ETF每日分析报告" in head:
            return False
        # 数据质量 < 50 也认为不合格，需要重试
        m = __import__("re").search(r"数据质量[^\d]*(\d+)/100", head)
        if m and int(m.group(1)) < 50:
            return False
        # 未刷新 ETF 超过 2 只也不合格，需要重试（虽然脚本会写"未就绪"报告，但双重保险）
        if "数据时效性问题" in head:
            return False
        return True
    except Exception:
        return False


def generate_report(target_date: str = None):
    now = datetime.now()
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 云端报告生成...")

    if target_date:
        target_ts = pd.Timestamp(target_date)
        print(f"  补生成模式: {target_ts.strftime('%Y-%m-%d')}")
        expected_date = target_ts  # 期望最后交易日为指定日期
        report_date_str = target_ts.strftime("%Y%m%d")
    else:
        target_ts = None
        print(f"  正常模式: 今日报告")
        # 期望最后交易日为今日（仅在交易日 15:30 后才合理）
        expected_date = pd.Timestamp(now.date())
        # 若今日是周末（周六/周日），则期望最后一个交易日为上周五
        # GitHub Actions cron 现在 21:00~23:00 每 15 分钟触发一次
        weekday = now.weekday()
        if weekday == 5:  # 周六
            expected_date = pd.Timestamp(now.date()) - pd.Timedelta(days=1)  # 周五
        elif weekday == 6:  # 周日
            expected_date = pd.Timestamp(now.date()) - pd.Timedelta(days=2)  # 周五
        report_date_str = expected_date.strftime("%Y%m%d")
    print(f"  期望最后交易日: {expected_date.strftime('%Y-%m-%d')}")

    # === 冗余 cron 门禁：今天报告已生成且数据合格就直接跳过 ===
    if not target_date and report_already_ready(report_date_str):
        size = os.path.getsize(os.path.join("reports", f"daily_report_{report_date_str}.md"))
        print(f"  ✅ 今日报告已存在且合格 ({size} bytes), 跳过生成")
        print(f"  (cron 冗余触发机制: 本次无需重复执行)")
        # 不生成 commit，git diff --staged --quiet 会直接退出不推送
        return

    indicators = TechnicalIndicators()
    signal_generator = SignalGenerator()
    report_generator = ReportGenerator()

    etf_results = {}
    all_warnings = []
    stale_data_etfs = []  # 记录数据未刷新的ETF

    for symbol, info in ETF_CONFIG.items():
        try:
            print(f"\n  处理 {symbol} ({info['name']})...")
            df = fetch_kline(symbol, info["exchange"], count=100,
                             expected_date=expected_date)
            if df.empty:
                all_warnings.append(f"{symbol}: akshare 获取失败")
                continue

            # 数据时效性最终检查（即使重试用尽，也要记录警告）
            if expected_date is not None and not df.empty:
                last_date = df["date"].iloc[-1]
                if last_date.date() != expected_date.date():
                    stale_data_etfs.append(symbol)
                    all_warnings.append(
                        f"{symbol}: 数据时效性问题 - 期望 {expected_date.strftime('%Y-%m-%d')}, "
                        f"实际最后日期 {last_date.strftime('%Y-%m-%d')}"
                    )

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

    # === 关键决策：数据未刷新到当日的 ETF 超过 2 只时，不生成误导性报告 ===
    stale_count = len(stale_data_etfs)
    total_etfs = len(ETF_CONFIG)
    # 阈值：超过 2 只（含）未刷新，或未刷新比例 >= 50%，判定为数据源未就绪
    data_stale = stale_count >= 2 or (total_etfs > 0 and stale_count / total_etfs >= 0.5)

    if etf_results and not data_stale:
        # 数据新鲜度 OK，生成正常报告
        quality = max(50, 100 - len(all_warnings) * 15)

        # 最后交易日：取所有ETF中最常见的日期
        all_last_dates = [result["data"]["date"].iloc[-1] for result in etf_results.values()]
        if all_last_dates:
            from collections import Counter
            date_counter = Counter(d.date() for d in all_last_dates)
            majority_date = date_counter.most_common(1)[0][0]
            last_trade_date = pd.Timestamp(majority_date).strftime("%Y-%m-%d")
        else:
            last_trade_date = "未知"

        warnings_list = ["云端生成，基于 akshare 真实日K线"]
        if stale_data_etfs:
            warnings_list.append(
                f"⚠️ 数据时效性问题: {', '.join(stale_data_etfs)} 数据可能未刷新到当日"
            )
        warnings_list.extend(all_warnings[:3])

        data_meta = {
            "source": "akshare(东方财富API) - GitHub Actions 云端生成",
            "last_trade_date": last_trade_date,
            "expected_date": expected_date.strftime("%Y-%m-%d") if expected_date else None,
            "validated": True,
            "quality_score": quality,
            "warnings": warnings_list
        }
        report = report_generator.generate_daily_report(etf_results, data_meta)

        if target_date:
            filepath = report_generator.save_report(report, f"daily_report_{target_date}.md")
        else:
            filepath = report_generator.save_report(report)
        print(f"\n  报告已保存: {filepath}")
        print(f"  数据质量: {quality}/100")
    else:
        # 数据未就绪，生成明确的错误报告，避免"看起来正确但内容是昨日数据"的误导
        os.makedirs("reports", exist_ok=True)
        date_str = target_date or datetime.now().strftime("%Y%m%d")
        if not etf_results:
            title = "## ⚠️ 数据获取失败"
            reason = "云端报告生成时无法获取 ETF 数据。"
        else:
            title = "## ⚠️ 数据源未就绪（数据为前一交易日）"
            reason = (
                f"新浪/东财 API 在 GitHub Actions 服务器（美国）上尚未刷新到 "
                f"{expected_date.strftime('%Y-%m-%d') if expected_date else '当日'} 的收盘数据，"
                f"当前 {stale_count}/{total_etfs} 只 ETF 数据停留在前一交易日。"
                f"\n\n**请等待次日本地同步补全，或手动触发 GitHub Actions Workflow。**"
            )
        error_report = f"""# ⚠️ ETF每日分析报告 - 数据未就绪

**分析日期**: {date_str}

{title}

{reason}

### 原因说明
1. GitHub Actions 服务器部署在美国东/西海岸
2. 新浪财经 / 东方财富 API 在海外的数据刷新比国内慢 1~3 小时
3. 如果此时强行生成报告会混入前一天的收盘价，造成交易建议严重错误

### 数据时效性检查结果
"""
        for sym in ETF_CONFIG.keys():
            result = etf_results.get(sym)
            if result is not None:
                last_dt = result["data"]["date"].iloc[-1].strftime("%Y-%m-%d")
                close_px = result["data"]["close"].iloc[-1]
                mark = " ❌" if sym in stale_data_etfs else " ✅"
                error_report += f"- **{sym}**: 最后日期 {last_dt}, 收盘价={close_px:.4f}{mark}\n"
            else:
                error_report += f"- **{sym}**: 获取失败 ❌\n"
        error_report += "\n### 警告信息\n"
        for w in all_warnings:
            error_report += f"- {w}\n"
        error_report += f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n"

        filepath = os.path.join("reports", f"daily_report_{date_str}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(error_report)
        print(f"\n  数据未就绪报告已保存: {filepath}")
        print(f"  未刷新 ETF: {stale_count}/{total_etfs}  警告数: {len(all_warnings)}")

    # 调试：列出 reports/ 目录内容（跨平台）
    print("\n  === reports/ 目录内容 ===")
    try:
        if os.path.exists("reports"):
            files = sorted(os.listdir("reports"))
            for f in files:
                fp = os.path.join("reports", f)
                size = os.path.getsize(fp) if os.path.isfile(fp) else 0
                print(f"  {f}  ({size} bytes)")
        else:
            print("  (reports 目录不存在)")
    except Exception as e:
        print(f"  (列目录错误: {e})")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_report(target_date=date_arg)
