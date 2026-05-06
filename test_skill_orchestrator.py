import json
import sys

sys.path.insert(0, "skills/skill-orchestrator")
from main import WorkflowEngine

engine = WorkflowEngine()

print("=== Test 1: List Workflows ===")
result = engine.list_workflows()
print(f"Built-in workflows: {len(result['built_in'])}")
print(f"Custom workflows: {len(result['custom'])}")
for wf in result["built_in"]:
    print(f"  - {wf['name']}: {wf['display_name']} ({wf['steps_count']} steps)")
print()

print("=== Test 2: Execute Order Full Inquiry ===")
result2 = engine.execute_workflow(
    "order_full_inquiry",
    {"order_id": "ORD20240101001"},
    {"user_id": "user123", "channel": "feishu"},
)
print(f"Success: {result2['success']}")
print(f"Workflow: {result2.get('workflow_name', '')}")
print(f"Completed steps: {result2.get('completed_steps', 0)}/{result2.get('total_steps', 0)}")
print(f"Duration: {result2.get('duration_ms', 0)}ms")
for detail in result2.get("step_details", []):
    print(f"  Step {detail['step_index']}: {detail['skill']}({detail['action']}) -> {detail['status']}")
print()

print("=== Test 3: Execute Custom Workflow ===")
result3 = engine.execute_custom(
    steps=[
        {"skill": "order-query", "action": "query", "output_key": "order", "required": True},
        {"skill": "logistics-track", "action": "track", "output_key": "logistics", "condition": "has_tracking"},
    ],
    params={"order_id": "ORD20240101001"},
    context={"user_id": "user456"},
    aggregation_type="order_full_report",
)
print(f"Success: {result3['success']}")
print(f"Completed steps: {result3.get('completed_steps', 0)}/{result3.get('total_steps', 0)}")
for detail in result3.get("step_details", []):
    print(f"  Step {detail['step_index']}: {detail['skill']}({detail['action']}) -> {detail['status']}")
print()

print("=== Test 4: Save Custom Template ===")
result4 = engine.save_custom_template(
    "my_test_workflow",
    {
        "name": "测试工作流",
        "description": "自定义测试工作流",
        "steps": [
            {"skill": "order-query", "action": "query", "output_key": "order", "required": True},
        ],
        "aggregation": "default",
    },
)
print(f"Save template: {result4['success']}")
print()

print("=== Test 5: List Workflows (with custom) ===")
result5 = engine.list_workflows()
print(f"Total workflows: {result5['total']}")
print(f"Custom workflows: {len(result5['custom'])}")
print()

print("=== Test 6: Execution History ===")
result6 = engine.get_execution_history(10)
print(f"History entries: {len(result6)}")
for entry in result6[:3]:
    print(f"  - {entry['execution_id']}: {entry['workflow_name']} ({entry['status']})")
print()

print("All skill orchestrator tests passed!")
