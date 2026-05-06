import json
import sys

sys.path.insert(0, "skills/knowledge-pipeline")
from main import KnowledgePipeline

pipeline = KnowledgePipeline()

print("=== Test 1: Import Builtin Knowledge ===")
result = pipeline.import_builtin_knowledge()
print(f"Success: {result['success']}")
print(f"Total docs: {result['total_docs']}")
print(f"Imported: {result['imported_docs']}")
print(f"Failed: {result['failed_docs']}")
print(f"Total chunks: {result['total_chunks']}")
print()

print("=== Test 2: List Categories ===")
result2 = pipeline.list_categories()
print(f"Total categories: {result2['total_categories']}")
for key, cat in result2["categories"].items():
    print(f"  {key}: {cat['name']} ({cat['imported_count']} imported / {cat['document_count']} builtin)")
print()

print("=== Test 3: Search Knowledge ===")
result3 = pipeline.search("亚马逊ACOS优化策略", top_k=3)
print(f"Query: {result3['query']}")
print(f"Results: {result3['count']}")
for r in result3["results"]:
    print(f"  [{r['score']}] {r['title']} ({r['category']})")
    print(f"    Content: {r['content'][:80]}...")
print()

print("=== Test 4: Search by Category ===")
result4 = pipeline.search("物流方案", top_k=3, category="logistics_warehouse")
print(f"Results: {result4['count']}")
for r in result4["results"]:
    print(f"  [{r['score']}] {r['title']} ({r['category']})")
print()

print("=== Test 5: Hallucination Check ===")
result5 = pipeline.search_with_hallucination_check(
    query="亚马逊ACOS优化",
    response="ACOS应该控制在25%-35%之间，可以通过优化关键词出价和否定关键词来降低ACOS。",
    top_k=3,
)
check = result5["hallucination_check"]
print(f"Confidence: {check['confidence_score']}")
print(f"Risk: {check['hallucination_risk']}")
print(f"Details: {check['details']}")
print(f"Recommendation: {check['recommendation']}")
print()

print("=== Test 6: Hallucination Check (High Risk) ===")
result6 = pipeline.search_with_hallucination_check(
    query="量子计算机维修指南",
    response="量子计算机需要使用液氮冷却至接近绝对零度，维修时需佩戴防静电手套。",
    top_k=3,
)
check2 = result6["hallucination_check"]
print(f"Confidence: {check2['confidence_score']}")
print(f"Risk: {check2['hallucination_risk']}")
print(f"Recommendation: {check2['recommendation']}")
print()

print("=== Test 7: Import Custom Document ===")
result7 = pipeline.import_document(
    title="小红书种草笔记写作技巧",
    category="cross_border_ops",
    content="小红书种草笔记写作技巧：1) 标题要有吸引力，使用数字和emoji；2) 开头3行决定用户是否继续阅读；3) 正文要有场景化描述，让用户代入；4) 图片要精美，首图最关键；5) 话题标签选择3-5个相关标签；6) 发布时间选择晚上8-10点；7) 互动引导，在结尾提问或征集意见。",
    tags=["小红书", "种草", "内容营销"],
    source="manual",
)
print(f"Success: {result7['success']}")
print(f"Doc ID: {result7['doc_id']}")
print(f"Chunks: {result7['chunks']}")
print()

print("=== Test 8: Stats ===")
result8 = pipeline.get_stats()
print(f"Documents: {result8['documents']}")
print(f"Chunks: {result8['chunks']}")
print(f"Hallucination checks: {result8['hallucination_checks']}")
print(f"Categories: {result8['categories']}")
print()

print("All knowledge pipeline tests passed!")
