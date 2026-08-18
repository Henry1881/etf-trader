"""
详细 debug 通达信 MCP HTTP 响应 (修正版)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
import json

MCP_URL = "https://txmcp.tdx.com.cn:3001/traemcp"
API_KEY = "TDX-33bd9b128f6d09470e9c49bf30722a8a"

requests.packages.urllib3.disable_warnings()

def step1_init():
    print("[Step 1] initialize with proper Accept header...")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "EtF-Trader-Debug", "version": "1.0.0"}
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {API_KEY}"
    }
    r = requests.post(MCP_URL, json=payload, headers=headers, timeout=30, verify=False)
    print(f"  HTTP {r.status_code}")
    print(f"  Response headers: {dict(r.headers)}")
    text = r.text
    print(f"  Response text:")
    print("    " + text[:2000].replace("\n", "\n    "))
    sess = r.headers.get("Mcp-Session-Id")
    print(f"\n  Session: {sess}")
    return sess, text

def step2_call(session_id, question, rng, label=""):
    print(f"\n[Step 2 {label}] call tdx_wenda_quotes question={question!r} range={rng!r}...")
    payload = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "tdx_wenda_quotes",
            "arguments": {
                "question": question,
                "range": rng,
                "size": 10
            }
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {API_KEY}"
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    r = requests.post(MCP_URL, json=payload, headers=headers, timeout=30, verify=False)
    print(f"  HTTP {r.status_code}")
    text = r.text
    print(f"  text length = {len(text)}")
    print("  Full text:")
    print("    " + text[:4000].replace("\n", "\n    "))
    return text

# 1. Initialize
sess, init_text = step1_init()

# 2. 用 run_mcp 中成功过的组合测试
# 组合1: 588170.SH + AG
resp = step2_call(sess, "588170.SH", "AG", label="上交所 588170 .SH+AG")

# 组合2: 159611 最新价 涨跌幅 + JJ
resp = step2_call(sess, "159611 最新价 涨跌幅", "JJ", label="深交所 159611 +JJ关键词")

# 组合3: 588170 + SH
resp = step2_call(sess, "588170 最新价 涨跌幅 开盘价 最高价 最低价 成交量", "SH", label="上交所 588170 + SH")
