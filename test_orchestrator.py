import json
import sys

sys.path.insert(0, "skills/agent-orchestrator")
from main import AgentOrchestrator

orchestrator = AgentOrchestrator()

print("=== Test 1: Order Query ===")
result = orchestrator.process(
    "帮我查一下订单ORD20240101001的物流状态",
    {"user_id": "user123", "channel": "feishu"},
)
p = result["perception"]
d = result["decision"]
print(f"Intent: {p['intent']['intent']} ({p['intent']['intent_label']})")
print(f"Confidence: {d['decision']['confidence']}")
print(f"Action: {d['decision']['action']}")
print(f"Entities: {p['entities']}")
print(f"Skills: {[s['name'] for s in d['skill_plan']['skills']]}")
print(f"Response: {result['response']['message']}")
print()

print("=== Test 2: Listing Gen ===")
result2 = orchestrator.process(
    "帮我生成一个亚马逊的Listing，产品是蓝牙耳机",
    {"user_id": "user456", "channel": "feishu"},
)
p2 = result2["perception"]
d2 = result2["decision"]
print(f"Intent: {p2['intent']['intent']} ({p2['intent']['intent_label']})")
print(f"Confidence: {d2['decision']['confidence']}")
print(f"Action: {d2['decision']['action']}")
print(f"Entities: {p2['entities']}")
print(f"Skills: {[s['name'] for s in d2['skill_plan']['skills']]}")
print()

print("=== Test 3: Complaint ===")
result3 = orchestrator.process(
    "我要投诉，产品太差了，要求退款",
    {"user_id": "user789", "channel": "wework", "customer_tier": "VIP"},
)
p3 = result3["perception"]
d3 = result3["decision"]
print(f"Intent: {p3['intent']['intent']} ({p3['intent']['intent_label']})")
print(f"Sentiment: {p3['sentiment']['sentiment']} ({p3['sentiment']['sentiment_label']})")
print(f"Confidence: {d3['decision']['confidence']}")
print(f"Action: {d3['decision']['action']}")
print(f"Require Human: {p3['sentiment']['require_human']}")
print()

print("=== Test 4: XHS Content ===")
result4 = orchestrator.process(
    "帮我写一篇小红书种草笔记，关于智能手表",
    {"user_id": "user001", "channel": "feishu"},
)
p4 = result4["perception"]
d4 = result4["decision"]
print(f"Intent: {p4['intent']['intent']} ({p4['intent']['intent_label']})")
print(f"Skills: {[s['name'] for s in d4['skill_plan']['skills']]}")
print(f"Agent: {d4['agent_routing']['agent_id']}")
print()

print("=== Test 5: Skill Registry ===")
registry = orchestrator.get_skill_registry()
print(f"Registered skills: {len(registry['skills'])}")
print(f"Intent mappings: {len(registry['intent_map'])}")
for name, info in registry["skills"].items():
    print(f"  - {name}: {info['description']} ({info['domain']})")
print()

print("=== Test 6: Pipeline Stats ===")
stats = orchestrator.get_pipeline_stats(24)
print(f"Total conversations: {stats.get('total_conversations', 0)}")
print(f"Total messages: {stats.get('total_messages', 0)}")

print("\nAll tests passed!")
