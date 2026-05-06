import json
import sys
from datetime import datetime

sys.path.insert(0, "skills/cron-engine")
from main import CronEngine, CronParser

engine = CronEngine()

print("=== Test 1: Init Builtin Jobs ===")
result = engine.init_builtin_jobs()
print(f"Success: {result['success']}")
print(f"Created: {result['created']}, Updated: {result['updated']}, Total: {result['total']}")
print()

print("=== Test 2: List Jobs ===")
result2 = engine.list_jobs()
print(f"Total jobs: {result2['total']}")
for job in result2["jobs"]:
    status = "ON" if job["enabled"] else "OFF"
    next_run = job.get("next_run", "N/A")
    human = job.get("humanized_schedule", "")
    print(f"  [{status}] {job['name']} ({job['display_name']}) - {job['cron_expr']} - Next: {next_run}")
print()

print("=== Test 3: Validate Cron Expressions ===")
test_exprs = [
    "0 9 * * *",
    "*/10 * * * *",
    "0 */1 * * *",
    "0 18 * * 5",
    "0 8 * * 1-5",
    "invalid",
    "0 25 * * *",
]
for expr in test_exprs:
    result3 = engine.validate_cron(expr)
    if result3["valid"]:
        print(f"  {expr} -> {result3['humanized']} | Next: {result3['next_run']}")
    else:
        print(f"  {expr} -> INVALID: {result3['error']}")
print()

print("=== Test 4: Trigger Job ===")
result4 = engine.trigger_job("daily-ai-report")
print(f"Success: {result4['success']}")
print(f"Execution ID: {result4['execution_id']}")
print(f"Duration: {result4['duration_ms']}ms")
if result4["success"]:
    print(f"Result: {result4['result']}")
print()

print("=== Test 5: Trigger Opinion Monitor ===")
result5 = engine.trigger_job("opinion-monitor")
print(f"Success: {result5['success']}")
if result5["success"]:
    print(f"Result: {result5['result']}")
print()

print("=== Test 6: Add Custom Job ===")
result6 = engine.add_job({
    "name": "custom-metrics",
    "display_name": "自定义指标监控",
    "cron_expr": "0 */2 * * 1-5",
    "description": "工作日每2小时检查业务指标",
    "agent": "ecommerce",
    "skill": "report-gen",
    "action": "check_metrics",
    "params": {"metrics": ["sales", "inventory", "ads"]},
    "channel": "feishu",
    "target": "ops_group",
})
print(f"Success: {result6['success']}")
print()

print("=== Test 7: Toggle Job ===")
result7 = engine.toggle_job("custom-metrics", False)
print(f"Success: {result7['success']}, Enabled: {result7['enabled']}")
result7b = engine.toggle_job("custom-metrics", True)
print(f"Re-enabled: {result7b['enabled']}")
print()

print("=== Test 8: Executions ===")
result8 = engine.get_executions()
print(f"Total executions: {result8['total']}")
for exec in result8["executions"][:3]:
    print(f"  {exec['job_name']} - {exec['status']} - {exec['started_at']} ({exec['duration_ms']}ms)")
print()

print("=== Test 9: Stats ===")
result9 = engine.get_stats()
print(f"Total jobs: {result9['total_jobs']} (enabled: {result9['enabled_jobs']}, disabled: {result9['disabled_jobs']})")
print(f"Total executions: {result9['total_executions']}")
print(f"Success rate: {result9['success_rate']}%")
print()

print("=== Test 10: CronParser Next Run ===")
now = datetime(2026, 4, 29, 8, 30, 0)
for expr in ["0 9 * * *", "*/10 * * * *", "0 18 * * 5"]:
    next_run = CronParser.next_run(expr, now)
    print(f"  {expr} after {now} -> {next_run}")
print()

print("=== Test 11: Check and Execute (dry run) ===")
result11 = engine.check_and_execute()
print(f"Checked at: {result11['checked_at']}")
print(f"Triggered count: {result11['triggered_count']}")
print()

print("All cron engine tests passed!")
