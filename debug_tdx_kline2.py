"""调试通达信 K 线数据原始响应"""
import sys
import os
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MCP_URL = "https://txmcp.tdx.com.cn:3001/traemcp"
API_KEY = "TDX-33bd9b128f6d09470e9c49bf30722a8a"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": f"Bearer {API_KEY}"
}

def parse_sse_response(response):
    text = response.text
    result = None
    
    for line in text.split('\n'):
        if line.startswith('data: '):
            data_str = line[6:]
            try:
                data = json.loads(data_str)
                if 'result' in data:
                    result = data['result']
                elif 'error' in data:
                    result = {'error': data['error']}
            except json.JSONDecodeError:
                pass
    
    if result is None:
        try:
            data = json.loads(text)
            if 'result' in data:
                result = data['result']
        except:
            pass
    
    return result

# 初始化
print("初始化...")
init_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "EtF-Trader", "version": "1.0.0"}
    }
}

response = requests.post(MCP_URL, json=init_payload, headers=headers, timeout=30, verify=False)
session_id = response.headers.get("Mcp-Session-Id")
headers_with_session = headers.copy()
if session_id:
    headers_with_session["Mcp-Session-Id"] = session_id

print(f"✅ 连接成功\n")

# 获取 K 线数据并查看原始响应
print("获取 588170 K线数据...")
kline_payload = {
    "jsonrpc": "2.0",
    "id": 10,
    "method": "tools/call",
    "params": {
        "name": "tdx_kline",
        "arguments": {
            "code": "588170",
            "setcode": "1",
            "period": "daily",
            "count": 10
        }
    }
}

resp = requests.post(MCP_URL, json=kline_payload, headers=headers_with_session, timeout=30, verify=False)
result = parse_sse_response(resp)

print(f"HTTP 状态: {resp.status_code}")
print(f"\n原始响应文本 (前2000字符):")
print(resp.text[:2000])

if result:
    print(f"\n解析后的结果:")
    if 'content' in result:
        content = result['content']
        if isinstance(content, list) and len(content) > 0:
            text = content[0].get('text', '')
            print(f"\n文本内容 (前1500字符):")
            print(text[:1500])
            
            # 尝试解析 JSON
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                try:
                    json_str = text[json_start:json_end]
                    data = json.loads(json_str)
                    print(f"\nJSON 解析成功!")
                    print(f"顶级键: {list(data.keys())}")
                    
                    if 'ListHead' in data:
                        print(f"\nListHead: {json.dumps(data['ListHead'], ensure_ascii=False)[:500]}")
                    if 'KLineData' in data:
                        kline_data = data['KLineData']
                        print(f"\nKLineData 类型: {type(kline_data)}")
                        if isinstance(kline_data, list):
                            print(f"KLineData 长度: {len(kline_data)}")
                            if len(kline_data) > 0:
                                print(f"第一行: {kline_data[0]}")
                        elif isinstance(kline_data, dict):
                            print(f"KLineData 键: {list(kline_data.keys())[:10]}")
                except Exception as e:
                    print(f"JSON 解析失败: {e}")
    elif 'error' in result:
        print(f"\n错误: {result['error']}")
