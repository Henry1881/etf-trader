"""验证 tdx MCP 的 tdx_kline 是否能拿到真实历史 K 线"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_fetcher.tdx_data_fetcher import TDXDataFetcher
from src.utils.config_loader import ConfigLoader

cfg = ConfigLoader()
key = cfg.get("tdx_api_key", "")
print(f"API Key: {key[:20]}...")

f = TDXDataFetcher(key)
ok = f.initialize()
print(f"初始化: {ok}")

if ok:
    for sym, ex in [("588170", "sh"), ("159622", "sz")]:
        print(f"\n>>> {sym} ({ex})")
        df = f.get_kline_data(sym, ex, count=100)
        if df is None or df.empty:
            print(f"  ❌ 无数据")
            continue
        print(f"  行数: {len(df)}")
        print(f"  列: {list(df.columns)}")
        print(f"  首行: {df.iloc[0].to_dict()}")
        print(f"  末行: {df.iloc[-1].to_dict()}")
        if len(df) >= 20:
            print(f"  MA_5  = {df['close'].tail(5).mean():.4f}")
            print(f"  MA_20 = {df['close'].tail(20).mean():.4f}")
        if len(df) >= 60:
            print(f"  MA_60 = {df['close'].tail(60).mean():.4f}")
