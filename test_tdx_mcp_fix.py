"""
测试修复后的通达信 MCP ETF 数据获取
运行: python test_tdx_mcp_fix.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_fetcher.tdx_data_fetcher import TDXDataFetcher

API_KEY = "TDX-33bd9b128f6d09470e9c49bf30722a8a"

TEST_CASES = [
    # (代码, 交易所, 说明)
    ("588170", "sh", "科创半导体ETF华夏 (上证)"),
    ("159611", "sz", "电力ETF广发 (深证)"),
    ("159227", "sz", "航天航空ETF华夏 (深证)"),
    ("159272", "sz", "机器人ETF富国 (深证)"),
    ("159622", "sz", "创新药ETF东财 (深证)"),
]

def main():
    print("=" * 60)
    print("通达信 MCP ETF 查询修复验证测试")
    print("=" * 60)
    
    fetcher = TDXDataFetcher(API_KEY)
    print("\n[1] 初始化 MCP 连接...")
    ok = fetcher.initialize()
    print(f"    初始化: {'✅ 成功' if ok else '❌ 失败'}")
    
    if not ok:
        print("无法初始化，退出")
        return
    
    print(f"    Session ID: {fetcher.session_id}")
    
    print("\n[2] search_etf (搜索 588170)...")
    results = fetcher.search_etf("588170")
    for r in results[:3]:
        print(f"    找到: {r['code']} {r['name']} (market={r['market']})")
    if not results:
        print("    无结果")
    
    print("\n[3] get_realtime_quote (5只 ETF)...")
    
    all_pass = True
    
    for code, exchange, desc in TEST_CASES:
        print(f"\n  --- {code} {desc} ---")
        quote = fetcher.get_realtime_quote(code, exchange)
        
        if not quote:
            print(f"    ❌ 返回空数据")
            all_pass = False
            continue
        
        price = quote.get('price', 0)
        chg_pct = quote.get('change_pct', 0)
        name = quote.get('name', '')
        vol = quote.get('volume', 0)
        rng = quote.get('range_used', '')
        
        if price == 0:
            print(f"    ❌ price=0 数据无效")
            all_pass = False
        else:
            print(f"    ✅ 名称: {name}")
            print(f"       价格: {price}")
            print(f"       涨跌幅: {chg_pct:+.2f}%")
            print(f"       昨收:   {quote.get('prev_close')}")
            print(f"       开/高/低: {quote.get('open')}/{quote.get('high')}/{quote.get('low')}")
            print(f"       成交量(手): {vol}")
            print(f"       range: {rng}")
        
        # K 线测试
        kline = fetcher.get_kline_data(code, exchange)
        if kline is not None and not kline.empty:
            row = kline.iloc[-1]
            print(f"    ✅ K 线: {row['date'].date()} 收={row['close']}")
        else:
            print(f"    ⚠️ K 线: 无（可用历史数据方案代替）")
    
    print("\n[4] health_check...")
    hc = fetcher.health_check()
    print(f"    健康检查: {'✅ 通过' if hc else '❌ 失败'}")
    if not hc:
        all_pass = False
    
    print("\n" + "=" * 60)
    if all_pass:
        print("✅ 全部测试通过！修复有效。")
    else:
        print("⚠️ 部分测试未通过，请检查上方日志")
    print("=" * 60)


if __name__ == "__main__":
    main()
