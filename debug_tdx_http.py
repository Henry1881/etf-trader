"""
详细 debug 通达信 MCP HTTP 响应
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
import json

MCP_URL = "https://txmcp.tdx.com.cn:3001/traemcp"
API_KEY = "TDX-33bd9b128f6d09470e9c49bf30722a8a"

requests.packages.urllib3.disable_warnings()

def step1_init():
    print("[Step 1] initialize...")
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
        "Authorization": f"Bearer {API_KEY}"
    }
    r = requests.post(MCP_URL, json=payload, headers=headers, timeout=30, verify=False)
    print(f"  HTTP {r.status_code}")
    print(f"  Response headers: {dict(r.headers)}")
    print(f"  Response text (first 800 chars):")
    print("    " + r.text[:800].replace("\n", "\n    "))
    sess = r.headers.get("Mcp-Session-Id")
    print(f"  Session: {sess}")
    return sess

def step2_call(session_id, question, rng):
    print(f"\n[Step 2] call tdx_wenda_quotes question={question!r} range={rng!r}...")
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
        "Authorization": f"Bearer {API_KEY}"
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    
    r = requests.post(MCP_URL, json=payload, headers=headers, timeout=30, verify=False)
    print(f"  HTTP {r.status_code}")
    text = r.text
    print(f"  text length = {len(text)}")
    # 完整打印，不要截断
    if len(text) < 3000:
        print("  Full text:")
        print("    " + text.replace("\n", "\n    "))
    else:
        print("  text (first 2500 chars):")
        print("    " + text[:2500].replace("\n", "\n    "))

# 测试 run_mcp 中成功的几种组合
sess = step1_init()

# 组合1: 588170.SH + AG (run_mcp 中成功过)
step2_call(sess, "588170.SH", "AG")

# 组合2: 159611 最新价 涨跌幅 + JJ (run_mcp 中成功过)
step2_call(sess, "159611 最新价 涨跌幅", "JJ")

# 组合3: search 用的组合
step2_call(sess, "588170", "AG")
