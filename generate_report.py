import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from src.data_fetcher.etf_data_fetcher import ETFDataFetcher
from src.indicators.technical_indicators import TechnicalIndicators
from src.signal_engine.signal_generator import SignalGenerator
from src.reporter.report_generator import ReportGenerator
from src.utils.config_loader import ConfigLoader


def _validate_price_fields(etf_symbol: str, df: pd.DataFrame) -> list:
    warnings = []
    if df.empty:
        return warnings

    last = df.iloc[-1]
    close = last["close"]
    open_price = last["open"] if "open" in df.columns else None
    high = last["high"] if "high" in df.columns else None
    low = last["low"] if "low" in df.columns else None
    volume = last["volume"] if "volume" in df.columns else None
    amount = last["amount"] if "amount" in df.columns else None

    if pd.isna(close) or close <= 0:
        warnings.append(f"❌ {etf_symbol}: 收盘价异常 ({close})")
        return warnings

    if high is not None and low is not None:
        if high < low:
            warnings.append(f"❌ {etf_symbol}: 最高价({high}) < 最低价({low})")
        if close > high or close < low:
            warnings.append(f"⚠️ {etf_symbol}: 收盘价({close:.3f}) 超出 最高({high:.3f})/最低({low:.3f}) 范围")
        if open_price is not None and not pd.isna(open_price):
            if open_price > high or open_price < low:
                warnings.append(f"⚠️ {etf_symbol}: 开盘价({open_price:.3f}) 超出 最高({high:.3f})/最低({low:.3f}) 范围")

    if volume is not None and not pd.isna(volume) and volume <= 0:
        warnings.append(f"❌ {etf_symbol}: 成交量为0")

    if amount is not None and not pd.isna(amount) and amount < 0:
        warnings.append(f"❌ {etf_symbol}: 成交额为负数 ({amount})")

    if len(df) >= 2:
        prev = df.iloc[-2]
        prev_close = prev["close"]
        if prev_close > 0:
            pct = abs((close - prev_close) / prev_close)
            if pct > 0.30:
                warnings.append(f"⚠️ {etf_symbol}: 涨跌幅超过30% ({pct*100:.1f}%)，请核实")

    return warnings


def generate_daily_report():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行每日报告任务...")
    
    config = ConfigLoader().config
    data_fetcher = ETFDataFetcher()
    indicators = TechnicalIndicators()
    signal_generator = SignalGenerator()
    report_generator = ReportGenerator()
    
    etf_results = {}
    etf_list = config.get("etf_list", [])
    data_meta = {
        "source": "akshare/东方财富",
        "last_trade_date": "未知",
        "validated": False,
        "quality_score": 0,
        "warnings": []
    }
    all_valid = True
    total_warnings = []

    for etf in etf_list:
        try:
            print(f"  正在处理 ETF {etf['symbol']} ({etf['name']})...")
            df = data_fetcher.get_etf_daily_data(etf["symbol"], etf["exchange"])
            if df.empty:
                print(f"  ETF {etf['symbol']} 数据为空，跳过")
                total_warnings.append(f"ETF {etf['symbol']}: 数据获取失败")
                continue

            last_date = df["date"].iloc[-1]
            data_meta["last_trade_date"] = last_date.strftime("%Y-%m-%d")

            field_warnings = _validate_price_fields(etf["symbol"], df)
            if field_warnings:
                all_valid = False
                total_warnings.extend(field_warnings)
                for w in field_warnings:
                    print(f"  {w}")

            close = df["close"].iloc[-1]
            high = df["high"].iloc[-1]
            low = df["low"].iloc[-1]

            if len(df) >= 2:
                prev_close = df["close"].iloc[-2]
                if abs(close - prev_close) / prev_close > 0.30:
                    all_valid = False

            df_with_indicators = indicators.calculate_all(df)
            latest_indicators = indicators.get_latest_indicators(df_with_indicators)

            signal = signal_generator.generate_signal(latest_indicators)

            etf_results[etf["symbol"]] = {
                "name": etf["name"],
                "exchange": etf["exchange"],
                "signal": signal,
                "data": df_with_indicators
            }

            if config["output"]["console"]:
                report_generator.print_report(etf["name"], etf["symbol"], signal)

        except Exception as e:
            print(f"  处理ETF {etf['symbol']} 时出错: {str(e)}")
            total_warnings.append(f"ETF {etf['symbol']}: 处理异常 - {str(e)}")

    data_meta["validated"] = all_valid and len(etf_results) > 0
    data_meta["warnings"] = total_warnings

    if len(etf_results) == 5:
        data_meta["quality_score"] = 100 - len(total_warnings) * 20
    elif len(etf_results) > 0:
        data_meta["quality_score"] = 50 - len(total_warnings) * 10
    else:
        data_meta["quality_score"] = 0

    if config["output"]["markdown"]:
        daily_report = report_generator.generate_daily_report(etf_results, data_meta)
        filepath = report_generator.save_report(daily_report)
        if etf_results:
            print(f"\n  Markdown报告已保存: {filepath}")
            print(f"  数据质量评分: {data_meta['quality_score']}/100")
            if not all_valid:
                print(f"  ⚠️ 部分数据存在一致性问题，请仔细核对报告中的数据")
                for w in total_warnings:
                    print(f"    - {w}")
        else:
            print(f"\n  ⚠️ 所有ETF数据获取失败，已生成占位报告: {filepath}")
            print(f"  请检查网络连接或稍后重试")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 每日报告任务完成")


if __name__ == "__main__":
    generate_daily_report()