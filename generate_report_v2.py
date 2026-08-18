"""
ETF 每日报告生成脚本 - 增强版
支持多数据源：akshare (东方财富) + 通达信 MCP
当 akshare 失败时自动使用通达信实时行情数据
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from src.data_fetcher.etf_data_fetcher import ETFDataFetcher
from src.data_fetcher.tdx_data_fetcher import TDXDataFetcher
from src.indicators.technical_indicators import TechnicalIndicators
from src.signal_engine.signal_generator import SignalGenerator
from src.reporter.report_generator import ReportGenerator
from src.utils.config_loader import ConfigLoader


def _enrich_with_tdx_realtime(df: pd.DataFrame, tdx_fetcher, symbol: str, exchange: str) -> pd.DataFrame:
    """
    当 K 线数据不足时，使用通达信实时行情补充当日数据
    """
    if df.empty or len(df) < 30:
        print(f"    K线数据不足({len(df)}行)，尝试用通达信实时行情补充...")
        
        quote = tdx_fetcher.get_realtime_quote(symbol, exchange)
        if quote:
            # 获取历史 K 线（如果可用）
            try:
                tdx_kline = tdx_fetcher.get_kline_data(symbol, exchange, count=300)
                if tdx_kline is not None and not tdx_kline.empty:
                    return tdx_kline
            except Exception:
                pass
            
            # 如果 K 线获取失败，用实时行情创建当日数据
            today = datetime.now()
            new_row = {
                'date': pd.Timestamp(today.date()),
                'open': float(quote.get('open', 0)),
                'high': float(quote.get('high', 0)),
                'low': float(quote.get('low', 0)),
                'close': float(quote.get('price', quote.get('close', 0))),
                'volume': float(quote.get('volume', 0)),
                'amount': float(quote.get('amount', 0))
            }
            
            # 创建最小数据集（至少需要几天数据来计算指标）
            if df.empty:
                df = pd.DataFrame([new_row])
            else:
                # 更新最后一行或添加新行
                last_date = df['date'].iloc[-1]
                if last_date == new_row['date']:
                    # 更新最后一行
                    for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                        if col in df.columns:
                            df.loc[df.index[-1], col] = new_row[col]
                else:
                    # 添加新行
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
            print(f"    ✅ 已用通达信实时行情数据补充")
    
    return df


def _calculate_indicators_safe(df: pd.DataFrame, indicators: TechnicalIndicators) -> pd.DataFrame:
    """
    安全计算技术指标，处理数据不足的情况
    """
    try:
        if len(df) >= 30:
            return indicators.calculate_all(df)
        else:
            # 数据不足时，计算基础指标
            df = indicators.calculate_ma(df)
            df = indicators.calculate_rsi(df)
            return df
    except Exception as e:
        print(f"    技术指标计算出错: {e}")
        return df


def generate_daily_report():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行每日报告任务...")
    
    config = ConfigLoader().config
    data_fetcher = ETFDataFetcher()
    indicators = TechnicalIndicators()
    signal_generator = SignalGenerator()
    report_generator = ReportGenerator()
    
    # 获取通达信 fetcher（用于实时行情补充）
    tdx_fetcher = data_fetcher._tdx_fetcher if data_fetcher._tdx_available else None
    
    etf_results = {}
    etf_list = config.get("etf_list", [])
    data_meta = {
        "source": "akshare/东方财富",
        "last_trade_date": "未知",
        "validated": False,
        "quality_score": 0,
        "warnings": []
    }
    
    if tdx_fetcher:
        data_meta["source"] = "akshare + 通达信MCP"

    all_valid = True
    total_warnings = []

    for etf in etf_list:
        try:
            symbol = etf["symbol"]
            exchange = etf["exchange"]
            name = etf["name"]
            
            print(f"\n  正在处理 ETF {symbol} ({name})...")
            
            # 获取历史数据
            df = data_fetcher.get_etf_daily_data(symbol, exchange)
            
            if df.empty:
                print(f"    ⚠️ 历史数据获取失败，尝试通达信实时行情...")
                
                if tdx_fetcher:
                    # 尝试用通达信获取数据
                    tdx_df = tdx_fetcher.get_kline_data(symbol, exchange, count=300)
                    if tdx_df is not None and not tdx_df.empty:
                        df = tdx_df
                        print(f"    ✅ 通达信 K 线数据获取成功 ({len(df)}行)")
                    else:
                        # 最后尝试：实时行情
                        quote = tdx_fetcher.get_realtime_quote(symbol, exchange)
                        if quote:
                            df = pd.DataFrame([{
                                'date': pd.Timestamp(datetime.now().date()),
                                'open': float(quote.get('open', 0)),
                                'high': float(quote.get('high', 0)),
                                'low': float(quote.get('low', 0)),
                                'close': float(quote.get('price', 0)),
                                'volume': float(quote.get('volume', 0)),
                                'amount': float(quote.get('amount', 0))
                            }])
                            print(f"    ✅ 使用通达信实时行情数据")
                else:
                    print(f"    ❌ 无可用数据源，跳过")
                    total_warnings.append(f"{symbol}: 所有数据源均不可用")
                    all_valid = False
                    continue
            
            # 如果数据不足30行，尝试用通达信补充
            if tdx_fetcher and len(df) < 30:
                df = _enrich_with_tdx_realtime(df, tdx_fetcher, symbol, exchange)
            
            if df.empty:
                print(f"    ❌ 数据为空，跳过")
                all_valid = False
                continue
            
            # 验证数据
            last_close = df['close'].iloc[-1]
            if pd.isna(last_close) or last_close <= 0:
                print(f"    ❌ 收盘价异常，跳过")
                total_warnings.append(f"{symbol}: 收盘价异常")
                all_valid = False
                continue
            
            # 更新数据元信息
            last_date = df['date'].iloc[-1]
            if isinstance(last_date, pd.Timestamp):
                data_meta["last_trade_date"] = last_date.strftime("%Y-%m-%d")
            
            # 计算技术指标
            df_with_indicators = _calculate_indicators_safe(df, indicators)
            
            # 获取最新指标
            latest_indicators = indicators.get_latest_indicators(df_with_indicators)
            
            # 生成交易信号
            signal = signal_generator.generate_signal(latest_indicators)
            
            # 获取实时行情补充到信号中
            if tdx_fetcher:
                quote = tdx_fetcher.get_realtime_quote(symbol, exchange)
                if quote and quote.get('price', 0) > 0:
                    signal['current_price'] = quote['price']
                    signal['price_change'] = round((quote['price'] - quote.get('prev_close', quote['price'])) / quote.get('prev_close', quote['price']) * 100, 2)
            
            etf_results[symbol] = {
                "name": name,
                "exchange": exchange,
                "signal": signal,
                "data": df_with_indicators
            }
            
            print(f"    ✅ 处理完成，信号: {signal.get('action', 'N/A')}")
            
        except Exception as e:
            print(f"    ❌ 处理ETF {etf['symbol']} 时出错: {str(e)}")
            total_warnings.append(f"{etf['symbol']}: {str(e)}")
            all_valid = False

    # 更新数据质量评分
    if len(etf_results) == 5:
        data_meta["quality_score"] = 100 - len(total_warnings) * 20
    elif len(etf_results) > 0:
        data_meta["quality_score"] = 50 - len(total_warnings) * 10
    else:
        data_meta["quality_score"] = 0
    
    data_meta["validated"] = all_valid
    data_meta["warnings"] = total_warnings

    # 生成报告
    if etf_results:
        print(f"\n  生成 Markdown 报告...")
        daily_report = report_generator.generate_daily_report(etf_results, data_meta)
        filepath = report_generator.save_report(daily_report)
        print(f"  ✅ Markdown报告已保存: {filepath}")
        print(f"  数据质量评分: {data_meta['quality_score']}/100")
    else:
        print(f"\n  ⚠️ 所有ETF数据获取失败，已生成占位报告")
        # 生成错误报告
        error_report = f"""# ETF每日分析报告

**生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**状态**: ❌ 报告生成失败

## 错误信息

所有数据源均不可用，无法生成有效报告。

### 可能的原因：
1. 网络连接问题
2. 数据源服务暂时不可用
3. 非交易时段数据延迟

### 建议：
- 检查网络连接
- 稍后重试
- 查看日志获取详细错误信息

---

**免责声明**: 本报告仅供参考，不构成任何投资建议。
"""
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        error_path = os.path.join(reports_dir, f"daily_report_{datetime.now().strftime('%Y%m%d')}.md")
        with open(error_path, 'w', encoding='utf-8') as f:
            f.write(error_report)
        print(f"  错误报告已保存: {error_path}")

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 每日报告任务完成")


if __name__ == "__main__":
    generate_daily_report()
