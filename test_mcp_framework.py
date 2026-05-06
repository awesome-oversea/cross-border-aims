import json
import sys

sys.path.insert(0, "skills/mcp-framework")
from main import MCPFramework, MCPFourStageProtocol

framework = MCPFramework()

print("=== Test 1: List Servers ===")
result = {
    "servers": list(framework.adapters.keys()),
    "total": len(framework.adapters),
}
print(f"Total servers: {result['total']}")
for s in result["servers"]:
    print(f"  - {s}")
print()

print("=== Test 2: List Tools ===")
result2 = framework.list_tools()
print(f"Total tools: {result2['total_tools']}")
for server, tools in result2["servers"].items():
    print(f"  {server}: {list(tools.keys())}")
print()

print("=== Test 3: Ecommerce Tools ===")
result3 = framework.list_tools("ecommerce")
print(f"Ecommerce tools: {result3['count']}")
for name, info in result3["tools"].items():
    print(f"  {name}: {info['description']} (risk: {info['risk_level']})")
print()

print("=== Test 4: Social Media Tools ===")
result4 = framework.list_tools("social_media")
print(f"Social media tools: {result4['count']}")
for name, info in result4["tools"].items():
    print(f"  {name}: {info['description']} (risk: {info['risk_level']})")
print()

print("=== Test 5: Four Stage Protocol - Query Product ===")
four_stage = MCPFourStageProtocol(framework)
result5 = four_stage.process(
    "查商品",
    {"platform": "taobao", "params": {"platform": "taobao"}},
)
stages = result5["stages"]
print(f"Stage 1 (Intent): {stages['intent_recognition']['detected_intent']} (confidence: {stages['intent_recognition']['confidence']})")
print(f"Stage 2 (Negotiation): server={stages['capability_negotiation'].get('server')}, tool={stages['capability_negotiation'].get('tool')}")
print(f"Stage 3 (Call): status={stages['standardized_call']['status']}")
print(f"Stage 4 (Feedback): {stages['execution_feedback']['recommendation']}")
print(f"Overall success: {result5['success']}")
print()

print("=== Test 6: Four Stage Protocol - Manage Ad ===")
result6 = four_stage.process(
    "查看广告投放数据",
    {"platform": "taobao", "params": {"platform": "taobao"}},
)
stages6 = result6["stages"]
print(f"Intent: {stages6['intent_recognition']['detected_intent']}")
print(f"Server: {stages6['capability_negotiation'].get('server')}")
print(f"Recommendation: {stages6['execution_feedback']['recommendation']}")
print()

print("=== Test 7: Four Stage Protocol - Publish Content (Write) ===")
result7 = four_stage.process(
    "发布小红书种草笔记",
    {"platform": "xhs", "params": {"platform": "xhs", "content": {"title": "test"}}},
)
stages7 = result7["stages"]
print(f"Intent: {stages7['intent_recognition']['detected_intent']}")
print(f"Risk level: {stages7['capability_negotiation'].get('risk_level')}")
print(f"Stage 3 status: {stages7['standardized_call']['status']}")
print(f"Recommendation: {stages7['execution_feedback']['recommendation']}")
print()

print("=== Test 8: Four Stage Protocol - Auto Approve Write ===")
result8 = four_stage.process(
    "发布小红书种草笔记",
    {"platform": "xhs", "auto_approve": True, "params": {"platform": "xhs", "content": {"title": "test"}}},
)
stages8 = result8["stages"]
print(f"Stage 3 status: {stages8['standardized_call']['status']}")
print(f"Recommendation: {stages8['execution_feedback']['recommendation']}")
print()

print("=== Test 9: Four Stage Protocol - Unknown Intent ===")
result9 = four_stage.process("今天天气怎么样")
stages9 = result9["stages"]
print(f"Intent: {stages9['intent_recognition']['detected_intent']}")
print(f"Stage 2 status: {stages9['capability_negotiation'].get('status')}")
print()

print("=== Test 10: Health Check ===")
result10 = framework.health_check_all()
print(f"Overall healthy: {result10['overall_healthy']}")
for name, check in result10["servers"].items():
    print(f"  {name}: healthy={check.get('healthy', False)}, mode={check.get('mode', 'unknown')}")
print()

print("All MCP framework tests passed!")
