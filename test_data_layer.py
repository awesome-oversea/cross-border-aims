import json
import sys

sys.path.insert(0, "skills/data-layer")
from main import DataManager, ETLPipeline

dm = DataManager()
etl = ETLPipeline(dm)

print("=== Test 1: Table Stats ===")
result = dm.get_table_stats()
print(f"Total tables: {result['total_tables']}")
for name, info in result["tables"].items():
    print(f"  {name}: {info['count']} records ({info['description']})")
print()

print("=== Test 2: Insert User ===")
result2 = dm.insert_user({
    "user_id": "user-test-001",
    "channel": "feishu",
    "name": "测试用户",
    "role": "operator",
    "preferences": {"language": "zh", "timezone": "Asia/Shanghai"},
})
print(f"Success: {result2['success']}, user_id: {result2['user_id']}")
print()

print("=== Test 3: Insert Product ===")
result3 = dm.insert_product({
    "product_id": "prod-test-001",
    "platform": "taobao",
    "title": "蓝牙耳机降噪无线",
    "price": 199.9,
    "category": "电子产品",
    "selling_points": "主动降噪,蓝牙5.3,30小时续航",
    "bsr_rank": 156,
    "review_count": 234,
    "rating": 4.6,
    "monthly_sales": 1500,
})
print(f"Success: {result3['success']}, product_id: {result3['product_id']}")
print()

print("=== Test 4: Insert Order ===")
result4 = dm.insert_order({
    "order_id": "ord-test-001",
    "platform": "taobao",
    "order_no": "TB20260429001",
    "product_title": "蓝牙耳机降噪无线",
    "quantity": 2,
    "amount": 399.8,
    "status": "shipped",
    "buyer_name": "买家A",
    "tracking_number": "SF1234567890",
})
print(f"Success: {result4['success']}, order_id: {result4['order_id']}")
print()

print("=== Test 5: Insert Review ===")
result5 = dm.insert_review({
    "review_id": "rev-test-001",
    "platform": "taobao",
    "product_id": "prod-test-001",
    "content": "音质很好，降噪效果不错",
    "rating": 5,
    "sentiment": "positive",
    "sentiment_score": 0.92,
    "reviewer_name": "用户B",
})
print(f"Success: {result5['success']}, review_id: {result5['review_id']}")
print()

print("=== Test 6: Insert Session ===")
result6 = dm.insert_session({
    "session_id": "sess-test-001",
    "channel": "feishu",
    "user_id": "user-test-001",
    "agent_name": "ecommerce",
    "message": "帮我查一下蓝牙耳机的销量",
    "reply": "蓝牙耳机本月销量1500件，BSR排名156",
    "intent": "query_product",
    "confidence": 0.95,
    "skill_used": "listing-gen",
    "duration_ms": 1200,
})
print(f"Success: {result6['success']}")
print()

print("=== Test 7: Insert Content ===")
result7 = dm.insert_content({
    "content_id": "cnt-test-001",
    "type": "post",
    "platform": "xhs",
    "title": "蓝牙耳机种草笔记",
    "status": "published",
    "views": 5600,
    "likes": 320,
    "comments": 45,
    "shares": 28,
})
print(f"Success: {result7['success']}")
print()

print("=== Test 8: Query Orders ===")
result8 = dm.query_table("orders", {"platform": "taobao"}, limit=5)
print(f"Found: {result8['count']} orders")
for order in result8["data"]:
    print(f"  {order['order_no']} - {order['status']} - {order['amount']}")
print()

print("=== Test 9: Run ETL - Order Sync ===")
result9 = etl.run_pipeline("order_sync")
print(f"Success: {result9['success']}")
print(f"Processed: {result9.get('processed', 0)}, Inserted: {result9.get('inserted', 0)}, Updated: {result9.get('updated', 0)}")
print()

print("=== Test 10: Run ETL - Product Sync ===")
result10 = etl.run_pipeline("product_sync")
print(f"Success: {result10['success']}")
print(f"Processed: {result10.get('processed', 0)}, Inserted: {result10.get('inserted', 0)}")
print()

print("=== Test 11: Run ETL - Review Sync ===")
result11 = etl.run_pipeline("review_sync")
print(f"Success: {result11['success']}")
print(f"Processed: {result11.get('processed', 0)}, Inserted: {result11.get('inserted', 0)}")
print()

print("=== Test 12: List Pipelines ===")
result12 = etl.list_pipelines()
print(f"Total pipelines: {result12['total']}")
for name, pipe in result12["pipelines"].items():
    print(f"  {name}: {pipe['name']} ({pipe['schedule']})")
print()

print("=== Test 13: ETL Logs ===")
result13 = etl.get_pipeline_logs()
print(f"Total logs: {result13['total']}")
for log in result13["logs"][:3]:
    print(f"  {log['pipeline_name']} - {log['status']} - {log['records_processed']} records")
print()

print("=== Test 14: Data Quality Check ===")
result14 = etl.run_data_quality_check()
print(f"Tables checked: {result14['tables_checked']}")
print(f"Total issues: {result14['total_issues']}")
print(f"Overall quality: {result14['overall_quality']}")
if result14["issues"]:
    for issue in result14["issues"]:
        print(f"  [{issue['severity']}] {issue['table']}: {issue['issue']}")
print()

print("=== Test 15: Updated Stats ===")
result15 = dm.get_table_stats()
for name, info in result15["tables"].items():
    print(f"  {name}: {info['count']} records")
print()

print("All data layer tests passed!")
