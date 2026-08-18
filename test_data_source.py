"""
测试 ETF 数据源可用性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 测试 akshare
print("=" * 60)
print("测试 akshare 数据源...")
try:
    import akshare as ak
    df = ak.fund_etf_hist_em(symbol="588170", period="daily", adjust="", start_date="20260101", end_date="20260729")
    if df is not None and not df.empty:
        print(f"✅ akshare 可用！获取 {len(df)} 行数据")
        print(f"   列名: {list(df.columns)}")
        print(f"   最后5行:")
        print(df.tail())
    else:
        print("❌ akshare 返回空数据")
except Exception as e:
    print(f"❌ akshare 异常: {e}")

print()
print("=" * 60)
