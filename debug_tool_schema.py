"""
列出通达信原生工具的 inputSchema: tdx_quotes / tdx_kline / tdx_lookup_stock
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
import json

MCP_URL = "https://txmcp.tdx.com.cn:3001/traemcp"
API_KEY = "TDX-33bd9b128f6d09470e9c49bf30722a8a"
requests.packages.urllib3.disable_warnings()

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": f"Bearer {API_KEY}"
}

# 1. initialize + initialized
init = {
    "jsonrpc":"2.0","id":1,"method":"initialize",
    "params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"debug-schema","version":"1"}}
}
r = requests.post(MCP_URL, json=init, headers=headers, timeout=30, verify=False)
sess = r.headers.get("Mcp-Session-Id")
hdrs = {**headers, "Mcp-Session-Id": sess}

requests.post(MCP_URL, json={"jsonrpc":"2.0","method":"notifications/initialized"},
              headers=hdrs, timeout=30, verify=False)

# 2. tools/list
ls = {"jsonrpc":"2.0","id":2,"method":"tools/list"}
r = requests.post(MCP_URL, json=ls, headers=hdrs, timeout=30, verify=False)
text = r.text

# 提取完整 JSON
full_data = None
for line in text.split("\n"):
    if line.startswith("data: "):
        try:
            full_data = json.loads(line[6:])
        except:
            pass

if not full_data:
    print("ERROR: cannot parse data")
    sys.exit(1)

tools = full_data["result"]["tools"]
# 只看需要的 3 个
for t in tools:
    name = t.get("name")
    if name in ("tdx_quotes", "tdx_kline", "tdx_lookup_stock", "tdx_wenda_quotes"):
        print(f"\n=============== tool: {name} ===============")
        desc = t.get("description", "")
        # 截取前 300 字 description 讲清楚怎么用
        print("[description]", desc[:800])
        schema = t.get("inputSchema", {})
        print("[inputSchema]", json.dumps(schema, ensure_ascii=False, indent=2)[:3000])
