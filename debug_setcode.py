"""
用 tdx_quotes 查询ETF，测试不同 setcode：
  1=沪A 0=深A 33=基金(ETF/LOF)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
import json

MCP_URL = "https://txmcp.tdx.com.cn:3001/traemcp"
API_KEY = "TDX-33bd9b128f6d09470e9c49bf30722a8a"
requests.packages.urllib3.disable_warnings()

base_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": f"Bearer {API_KEY}"
}

# 1. initialize
init = {"jsonrpc":"2.0","id":1,"method":"initialize",
        "params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"t2","version":"1"}}}
r = requests.post(MCP_URL, json=init, headers=base_headers, timeout=30, verify=False)
sess = r.headers.get("Mcp-Session-Id")
hdrs = {**base_headers, "Mcp-Session-Id": sess}
requests.post(MCP_URL, json={"jsonrpc":"2.0","method":"notifications/initialized"}, headers=hdrs, timeout=30, verify=False)
print(f"Session = {sess}\n")

def call_tdx_quotes(code, setcode, label):
    payload = {
        "jsonrpc":"2.0","id":777,"method":"tools/call",
        "params":{"name":"tdx_quotes","arguments":{
            "code": code, "setcode": str(setcode),
            "hasHQInfo":"1","hasExtInfo":"1"
        }}
    }
    r = requests.post(MCP_URL, json=payload, headers=hdrs, timeout=30, verify=False)
    print(f"--- {label} | code={code} setcode={setcode} --- HTTP {r.status_code}")
    text = r.text
    # 提取 JSON
    for line in text.split("\n"):
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                if "result" in d:
                    c=d["result"]
                    if isinstance(c, dict) and "content" in c:
                        for blk in c["content"]:
                            t=blk.get("text","")
                            # 打印前3000字
                            print("  TEXT:", t[:3000].replace("\n","\n  "))
            except Exception as e:
                print("  PARSE ERR", e)
    print()

# ---- 测试 ----
# 上交所ETF 588170
call_tdx_quotes("588170", 1, "588170 setcode=1(沪A)")
call_tdx_quotes("588170", 33, "588170 setcode=33(基金)")

# 深交所ETF 159611 / 159227 / 159272 / 159622
for c in ["159611","159227","159272","159622"]:
    call_tdx_quotes(c, 0, f"{c} setcode=0(深A)")
    call_tdx_quotes(c, 33, f"{c} setcode=33(基金)")
