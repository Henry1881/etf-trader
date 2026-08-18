"""
列出通达信 MCP 服务器的可用 tools
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

# 1. initialize
init = {
    "jsonrpc":"2.0","id":1,"method":"initialize",
    "params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"debug-ls","version":"1"}}
}
r = requests.post(MCP_URL, json=init, headers=headers, timeout=30, verify=False)
sess = r.headers.get("Mcp-Session-Id")
print(f"Session: {sess}")

# 注意: 标准 MCP 需要 initialized 通知
notif = {
    "jsonrpc":"2.0","method":"notifications/initialized"
}
requests.post(MCP_URL, json=notif, headers={**headers, "Mcp-Session-Id": sess}, timeout=30, verify=False)

# 2. tools/list
ls = {"jsonrpc":"2.0","id":2,"method":"tools/list"}
r = requests.post(MCP_URL, json=ls, headers={**headers, "Mcp-Session-Id": sess}, timeout=30, verify=False)
text = r.text
print("=== tools/list response ===")
print(text[:8000])

# 3. 解析 SSE，看每个 tool 的 name
print("\n=== Parse tool names ===")
for line in text.split("\n"):
    if line.startswith("data: "):
        try:
            d = json.loads(line[6:])
            if "result" in d:
                tools = d["result"].get("tools", [])
                for t in tools:
                    name = t.get("name","?")
                    desc = (t.get("description","") or "")[:80]
                    print(f"  - {name} : {desc}")
        except Exception as e:
            pass
