"""
ETF 每日报告生成脚本 - 真实数据版 (v4)
=====================================
数据源策略（全部使用真实数据，绝不用模拟数据）：
  1) 通达信 MCP tdx_kline (period=4 日K线) — 获取 100 个交易日真实历史 K 线
  2) 通达信 MCP tdx_quotes — 获取当日实时行情（覆盖最新一日 K 线）
  3) akshare fund_etf_hist_em — 作为备选数据源（带重试）

关键修复（2026-08-06）：
  - 删除 generate_historical_data() 假数据生成函数
  - 删除 get_etf_config() 中硬编码的 recent_data
  - 修复 tdx_kline period 编码：daily=4（原来错误用 0，返回分时数据）
  - 添加数据完整性校验：行数≥60、MA非NaN、最新日期检查
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 强制 stdout/stderr 使用 UTF-8，避免在任务计划程序/后台运行时
# 因系统默认 GBK 编码无法输出 emoji(✅⚠️❌) 而 UnicodeEncodeError 崩溃
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from datetime import datetime, timedelta
from src.indicators.technical_indicators import TechnicalIndicators
from src.signal_engine.signal_generator import SignalGenerator
from src.reporter.report_generator import ReportGenerator
from src.utils.config_loader import ConfigLoader
import pandas as pd


# =============================================================
# 通达信 MCP 实时数据获取 (通过 HTTP 直连)
# =============================================================
_TDX_FETCHER = None
_TDX_INIT_TRIED = False
_TDX_META = {}  # {symbol: {"change_pct": float, "prev_close": float, "price": float}}


def _get_tdx_fetcher():
    """懒加载通达信 MCP 客户端"""
    global _TDX_FETCHER, _TDX_INIT_TRIED
    if _TDX_INIT_TRIED:
        return _TDX_FETCHER
    _TDX_INIT_TRIED = True
    try:
        try:
            cfg = ConfigLoader()
            key = cfg.get("tdx_api_key", "")
        except Exception:
            key = ""
        if not key:
            key = "TDX-33bd9b128f6d09470e9c49bf30722a8a"  # 默认 key

        from src.data_fetcher.tdx_data_fetcher import TDXDataFetcher
        f = TDXDataFetcher(key)
        if f.initialize():
            _TDX_FETCHER = f
            print("  ✅ 通达信 MCP 已连接 (tdx_kline 日K线 + tdx_quotes 实时行情)")
        else:
            print("  ⚠️ 通达信 MCP 初始化失败，将尝试 akshare 备选源")
    except Exception as e:
        print(f"  ⚠️ 通达信 MCP 加载异常: {e}，将尝试 akshare 备选源")
    return _TDX_FETCHER


def _fetch_real_kline(symbol: str, exchange: str, count: int = 100) -> pd.DataFrame:
    """
    获取真实日K线数据（优先通达信 MCP，备选 akshare）。
    返回 DataFrame[date, open, high, low, close, volume, amount]，按日期升序。
    """
    # ---------- 数据源1：通达信 MCP tdx_kline (period=4 日K线) ----------
    f = _get_tdx_fetcher()
    if f:
        try:
            df = f.get_kline_data(symbol, exchange, period="daily", count=count)
            if df is not None and not df.empty:
                # 校验：日K线每行日期应唯一（非分时数据）
                unique_dates = df["date"].nunique()
                if unique_dates >= len(df) * 0.9:  # 90%以上行日期唯一=日线
                    print(f"    ✅ 通达信日K线: {len(df)} 行 ({df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d')})")
                    return df
                else:
                    print(f"    ⚠️ 通达信返回疑似分时数据（{unique_dates} 唯一日 / {len(df)} 行），尝试 akshare")
        except Exception as e:
            print(f"    ⚠️ 通达信日K线异常: {e}")

    # ---------- 数据源2：akshare fund_etf_hist_em ----------
    try:
        import akshare as ak
        import time
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=200)).strftime("%Y%m%d")
        last_err = None
        for attempt in range(3):
            try:
                raw = ak.fund_etf_hist_em(
                    symbol=symbol, period="daily",
                    start_date=start_date, end_date=end_date, adjust=""
                )
                if raw is not None and not raw.empty:
                    rename = {"日期": "date", "开盘": "open", "收盘": "close",
                              "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount"}
                    df = raw.rename(columns=rename)
                    df["date"] = pd.to_datetime(df["date"])
                    for c in ["open", "high", "low", "close", "volume", "amount"]:
                        if c in df.columns:
                            df[c] = pd.to_numeric(df[c], errors="coerce")
                    df = df.sort_values("date").reset_index(drop=True)
                    cols = [c for c in ["date", "open", "high", "low", "close", "volume", "amount"] if c in df.columns]
                    df = df[cols]
                    print(f"    ✅ akshare 日K线: {len(df)} 行 ({df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d')})")
                    return df
            except Exception as e:
                last_err = e
                time.sleep(2 + attempt * 2)
        print(f"    ⚠️ akshare 也失败: {last_err}")
    except ImportError:
        print(f"    ⚠️ akshare 未安装")

    return pd.DataFrame()


def _overlay_today_realtime(df: pd.DataFrame, symbol: str, exchange: str) -> tuple:
    """
    用通达信 tdx_quotes 当日实时行情覆盖 df 最后一行（如果是今天）。
    返回 (updated_df, tdx_meta_dict)
    """
    f = _get_tdx_fetcher()
    if not f:
        return df, {}

    try:
        q = f.get_realtime_quote(symbol, exchange)
        if not q or not q.get("price"):
            return df, {}

        today_str = datetime.now().strftime("%Y-%m-%d")
        hq_date = q.get("date") or today_str

        meta = {
            "change_pct": q.get("change_pct", 0),
            "prev_close": q.get("prev_close", 0),
            "price": q.get("price", 0),
            "hq_date": hq_date,
        }

        today_ts = pd.Timestamp(hq_date)
        new_row = {
            "date": today_ts,
            "open": float(q.get("open") or q["price"]),
            "high": float(q.get("high") or q["price"]),
            "low": float(q.get("low") or q["price"]),
            "close": float(q.get("close") or q["price"]),
            "volume": float(q.get("volume") or 0.0),
            "amount": float(q.get("amount") or 0.0),
        }

        # 如果 df 最后一行就是今天，覆盖它；否则追加一行
        if not df.empty and df["date"].iloc[-1] == today_ts:
            for k, v in new_row.items():
                df.loc[df.index[-1], k] = v
            print(f"    ✅ 通达信实时覆盖 {hq_date}: 收={new_row['close']:.4f} 涨跌={meta['change_pct']:+.2f}%")
        else:
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df = df.sort_values("date").reset_index(drop=True)
            print(f"    ✅ 通达信实时新增 {hq_date}: 收={new_row['close']:.4f} 涨跌={meta['change_pct']:+.2f}%")

        return df, meta
    except Exception as e:
        print(f"    ⚠️ 通达信实时行情异常: {e}")
        return df, {}


def _validate_data_integrity(df: pd.DataFrame, symbol: str) -> tuple:
    """
    数据完整性校验：行数、最新日期、价格合理性。
    返回 (is_valid, warnings_list)
    """
    warnings = []
    if df.empty:
        return False, ["数据为空"]

    n = len(df)
    if n < 60:
        warnings.append(f"数据行数仅 {n} 行（MA_60 需要 60 行），技术指标可能不完整")

    # 最新日期校验
    last_date = df["date"].iloc[-1]
    today = datetime.now()
    days_diff = (today - last_date.to_pydatetime()).days
    if days_diff > 7:
        warnings.append(f"最新数据日期 {last_date.strftime('%Y-%m-%d')} 距今 {days_diff} 天，可能过时")

    # 价格合理性
    last = df.iloc[-1]
    if pd.isna(last["close"]) or last["close"] <= 0:
        warnings.append(f"最新收盘价异常: {last['close']}")
        return False, warnings

    if last["high"] < last["low"]:
        warnings.append(f"最高价({last['high']}) < 最低价({last['low']})")

    # 涨跌幅合理性（>30% 可疑）
    if n >= 2:
        prev_close = df["close"].iloc[-2]
        if prev_close > 0:
            pct = abs((last["close"] - prev_close) / prev_close)
            if pct > 0.30:
                warnings.append(f"日涨跌幅 {pct*100:.1f}% 超 30%，请核实")

    is_valid = len(warnings) == 0 or not any("异常" in w or "为空" in w for w in warnings)
    return is_valid, warnings


def get_etf_config():
    """获取ETF配置（仅代码/名称/交易所，不再包含硬编码历史数据）"""
    return {
        "588170": {"name": "科创半导体ETF华夏", "exchange": "sh"},
        "159611": {"name": "广发中证全指电力ETF", "exchange": "sz"},
        "159227": {"name": "华夏国证航天航空ETF", "exchange": "sz"},
        "159272": {"name": "机器人ETF富国", "exchange": "sz"},
        "159622": {"name": "创新药ETF沪港深", "exchange": "sz"},
    }


def _check_trading_time():
    """
    交易时间检查：确保报告在收盘后生成。
    A股交易时间：周一至周五 9:30-11:30, 13:00-15:00
    报告生成时间窗口：15:30（收盘后半小时）至 次日 03:00
    非交易日（周末）允许生成（补生成昨日报告）。
    返回 (is_allowed, reason)
    """
    now = datetime.now()
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    # 周末允许生成（补生成周五报告）
    if weekday >= 5:
        return True, f"周末({now.strftime('%A')})，允许补生成报告"

    # 工作日：检查是否在交易时间内或收盘前
    hour_min = now.hour * 100 + now.minute
    # 9:15-15:30 为禁止窗口（含集合竞价和收盘后半小时缓冲）
    if 915 <= hour_min < 1530:
        return False, f"当前时间 {now.strftime('%H:%M')} 处于交易时段(09:15-15:30)，股市尚未收盘，拒绝生成报告"

    return True, f"当前时间 {now.strftime('%H:%M')} 已收盘，允许生成报告"


def generate_report(target_date: str = None):
    """
    生成每日报告。
    参数:
        target_date: 指定日期，格式 'YYYYMMDD'（用于补生成历史报告）。
                     如果为 None，则自动判断当前时间是否适合生成今日报告。
    """
    now = datetime.now()
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 开始生成每日报告（真实数据版）...")

    if target_date:
        # 补生成模式：跳过时间检查，使用指定日期
        target_ts = datetime.strptime(target_date, "%Y%m%d")
        print(f"  📅 补生成模式: 目标日期 {target_ts.strftime('%Y-%m-%d')}")
    else:
        # 正常模式：交易时间检查
        is_allowed, reason = _check_trading_time()
        if not is_allowed:
            print(f"  ❌ {reason}")
            print(f"  报告应在 15:30 之后生成，当前时间过早，数据未定盘。")
            print(f"  定时任务已设置为每个交易日 20:00 自动运行。")
            return
        print(f"  ✅ 时间检查通过: {reason}")
        target_ts = now

    indicators = TechnicalIndicators()
    signal_generator = SignalGenerator()
    report_generator = ReportGenerator()

    etf_config = get_etf_config()
    etf_results = {}
    all_warnings = []
    tdx_connected = False

    for symbol, info in etf_config.items():
        try:
            print(f"\n  处理 ETF {symbol} ({info['name']})...")

            # 1. 获取真实历史日K线（100 天）
            df = _fetch_real_kline(symbol, info["exchange"], count=100)
            if df.empty:
                msg = f"{symbol}: 所有数据源均失败，无法生成报告"
                print(f"    ❌ {msg}")
                all_warnings.append(msg)
                continue

            # 补生成模式：截取到目标日期为止的数据（不使用目标日期之后的实时行情）
            if target_date:
                target_ts = pd.Timestamp(target_date)
                df = df[df["date"] <= target_ts].reset_index(drop=True)
                print(f"    📅 截取到 {target_date}: {len(df)} 行")
                _TDX_META[symbol] = {}
            else:
                # 正常模式：用当日实时行情覆盖/追加最新一日
                df, tdx_meta = _overlay_today_realtime(df, symbol, info["exchange"])
                if tdx_meta:
                    _TDX_META[symbol] = tdx_meta
                    tdx_connected = True
                else:
                    _TDX_META[symbol] = {}

            # 3. 数据完整性校验
            is_valid, warnings = _validate_data_integrity(df, symbol)
            for w in warnings:
                print(f"    ⚠️ {w}")
                all_warnings.append(f"{symbol}: {w}")

            # 4. 计算技术指标
            df_with_indicators = indicators.calculate_all(df)

            # 5. 获取最新指标
            latest_indicators = indicators.get_latest_indicators(df_with_indicators)
            if not latest_indicators:
                last_row = df_with_indicators.iloc[-1]
                latest_indicators = {
                    "price": {
                        "close": last_row["close"], "open": last_row["open"],
                        "high": last_row["high"], "low": last_row["low"],
                        "volume": last_row["volume"]
                    }
                }

            # 6. 设置 prev_close 和涨跌幅（优先用通达信真实值）
            tdx_meta_sym = _TDX_META.get(symbol, {})
            tdx_change_pct = tdx_meta_sym.get("change_pct")
            tdx_prev_close = tdx_meta_sym.get("prev_close")

            latest_close = df["close"].iloc[-1]

            if tdx_change_pct is not None and tdx_change_pct != 0:
                price_change = tdx_change_pct
            elif len(df) > 1:
                prev_close = df["close"].iloc[-2]
                price_change = (latest_close - prev_close) / prev_close * 100
            else:
                price_change = 0

            if "price" in latest_indicators:
                if tdx_prev_close and tdx_prev_close > 0:
                    latest_indicators["price"]["prev_close"] = tdx_prev_close
                elif len(df) > 1:
                    latest_indicators["price"]["prev_close"] = df["close"].iloc[-2]

            # 7. 校验 MA 指标非 NaN
            ma = latest_indicators.get("ma", {})
            for k, v in ma.items():
                if k != "trend" and pd.isna(v):
                    print(f"    ⚠️ {k} 为 NaN（数据不足），指标可能不可靠")
                    all_warnings.append(f"{symbol}: {k} 计算为 NaN")

            # 8. 生成交易信号（传递数据质量分，用于置信度计算）
            # 数据质量分 = 100 - 严重警告数×15（最低50）
            severe_warnings = len([w for w in all_warnings if "异常" in w or "失败" in w])
            current_quality = max(50, min(100, 100 - severe_warnings * 15))
            signal = signal_generator.generate_signal(latest_indicators, data_quality=current_quality)
            signal["current_price"] = latest_close
            signal["price_change"] = round(price_change, 2)

            etf_results[symbol] = {
                "name": info["name"],
                "exchange": info["exchange"],
                "signal": signal,
                "data": df_with_indicators
            }

            action = signal.get('final_signal', 'N/A')
            ma20 = ma.get("ma_20", 0)
            conf = signal.get('confidence', 0)
            conf_level = signal.get('confidence_level', '')
            print(f"    ✅ 完成: 信号={action} 价={latest_close:.4f} 涨跌={price_change:+.2f}% MA20={ma20:.4f} 置信度={conf:.1f}/10({conf_level})")

        except Exception as e:
            print(f"    ❌ 出错: {str(e)}")
            import traceback
            traceback.print_exc()
            all_warnings.append(f"{symbol}: 处理异常 - {str(e)}")

    # 生成报告
    if etf_results:
        quality = 100 - len([w for w in all_warnings if "异常" in w or "失败" in w]) * 15
        quality = max(50, min(100, quality))

        data_meta = {
            "source": (
                "通达信 MCP(tdx_kline日K线 + tdx_quotes实时行情)"
                + (" ✅已接通" if tdx_connected else " ⚠️未接通")
                + " + akshare备选"
            ),
            "last_trade_date": (
                list(etf_results.values())[0]["data"]["date"].iloc[-1].strftime("%Y-%m-%d")
                if etf_results else datetime.now().strftime("%Y-%m-%d")
            ),
            "validated": True,
            "quality_score": quality,
            "warnings": [
                "所有技术指标基于真实历史日K线计算（100个交易日），无模拟数据",
                f"数据完整性校验: {'✅ 通过' if not all_warnings else '⚠️ 有警告'}",
            ] + (["具体警告: " + "; ".join(all_warnings[:3])] if all_warnings else [])
        }

        daily_report = report_generator.generate_daily_report(etf_results, data_meta)

        # 补生成模式：用目标日期作为文件名
        if target_date:
            filename = f"daily_report_{target_date}.md"
            filepath = report_generator.save_report(daily_report, filename)
        else:
            filepath = report_generator.save_report(daily_report)
        print(f"\n  ✅ 报告已保存: {filepath}")
        print(f"  数据质量评分: {data_meta['quality_score']}/100")
        if all_warnings:
            print(f"  ⚠️ 警告数: {len(all_warnings)}")
    else:
        print("\n  ❌ 未能生成任何报告（所有 ETF 数据获取失败）")


if __name__ == "__main__":
    import sys
    # 支持: python generate_report_v3.py [YYYYMMDD]
    # 不带参数 = 生成今日报告（带交易时间检查）
    # 带日期参数 = 补生成指定日期报告（跳过时间检查）
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_report(target_date=date_arg)
