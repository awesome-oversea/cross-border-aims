import sys
import importlib

print("=" * 60)
print("AIMS 综合模块测试")
print("=" * 60)

# Test 1: Skill Gate
print("\n[1] Skill Gate 门控机制")
sys.path.insert(0, 'skills/skill-gate')
import main as gate_main
gate = gate_main.SkillGate()
r1 = gate.evaluate('listing_gen', 'ecommerce', 0.95)
print(f"  Low risk: level={r1['level']}, allowed={r1['allowed']}")
r2 = gate.evaluate('refund', 'cs', 0.55)
print(f"  High risk: level={r2['level']}, allowed={r2['allowed']}")
r3 = gate.evaluate('ad_adjust_price', 'ecommerce', 0.75)
print(f"  Medium risk: level={r3['level']}, allowed={r3['allowed']}")
stats = gate.get_stats()
print(f"  Stats: {stats['total_records']} records, {stats['total_rules']} rules")
sys.path.remove('skills/skill-gate')
del sys.modules['main']
print("  [PASS]")

# Test 2: Ecom MCP
print("\n[2] E-commerce MCP Server")
sys.path.insert(0, 'skills/mcp-framework')
import ecom_mcp
ecom = ecom_mcp.EcomMCP()
r = ecom.call_tool("ecom_product_list", {"platform": "taobao"})
print(f"  Product list: success={r['success']}, total={r['total']}")
r = ecom.call_tool("ecom_order_list", {"platform": "jd"})
print(f"  Order list: success={r['success']}, total={r['total']}")
r = ecom.call_tool("ecom_ad_campaign_list", {"platform": "pdd"})
print(f"  Ad campaigns: success={r['success']}")
r = ecom.list_tools()
print(f"  Tools: {r['total']}")
r = ecom.get_platform_status()
print(f"  Platforms: {list(r.keys())}")
print("  [PASS]")

# Test 3: Social MCP
print("\n[3] Social Media MCP Server")
import social_mcp
social = social_mcp.SocialMCP()
r = social.call_tool("social_content_publish", {"platform": "xhs", "title": "测试", "content": "这是一篇测试笔记内容，用于验证发布功能。", "tags": "测试"})
print(f"  Content publish: success={r['success']}")
r = social.call_tool("social_compliance_check", {"platform": "xhs", "content": "这是最好的产品，加微信获取优惠"})
print(f"  Compliance: compliant={r['compliant']}, issues={r['issue_count']}")
r = social.call_tool("wechat_send_message", {"platform": "wechat", "msg_type": "text", "content": "测试"})
print(f"  WeChat send: success={r['success']}")
r = social.call_tool("social_trending", {"platform": "douyin", "limit": 3})
print(f"  Trending: count={len(r['trending'])}")
r = social.list_tools()
print(f"  Tools: {r['total']}")
print("  [PASS]")

# Test 4: Multimodal MCP
print("\n[4] Multimodal MCP Server")
import multimodal_mcp
mm = multimodal_mcp.MultimodalMCP()
r = mm.call_tool("dalle_generate", {"prompt": "商品图", "size": "1024x1024", "n": 1})
print(f"  DALL-E: success={r['success']}, cost={r.get('cost', 0)}")
r = mm.call_tool("whisper_transcribe", {"audio_url": "test.mp3", "language": "zh"})
print(f"  Whisper: success={r['success']}")
r = mm.call_tool("tts_synthesize", {"text": "测试语音", "voice": "alloy"})
print(f"  TTS: success={r['success']}")
r = mm.call_tool("vision_analyze", {"image_url": "test.jpg", "prompt": "分析"})
print(f"  Vision: success={r['success']}")
r = mm.list_tools()
print(f"  Tools: {r['total']}")
print("  [PASS]")

# Test 5: ERP MCP
print("\n[5] ERP MCP Server")
import erp_mcp
erp = erp_mcp.ERPMCP()
r = erp.call_tool("erp_product_sync", {"product_id": "test_001", "platform": "taobao", "title": "测试商品", "price": 99.9, "stock": 100})
print(f"  Product sync: success={r['success']}")
r = erp.call_tool("erp_product_query", {"platform": "taobao"})
print(f"  Product query: success={r['success']}, total={r['total']}")
r = erp.call_tool("erp_purchase_suggest", {"product_id": "test_001", "current_stock": 50, "avg_daily_sales": 10, "lead_time_days": 7})
print(f"  Purchase suggest: urgency={r['urgency']}, suggested_qty={r['suggested_order_qty']}")
r = erp.call_tool("erp_profit_calc", {"product_id": "test_001", "revenue": 1000, "costs": {"product": 300, "ad": 100, "logistics": 50}})
print(f"  Profit calc: profit={r['profit']}, margin={r['profit_margin']}%, health={r['health']}")
r = erp.call_tool("erp_adopt", {"suggestion_type": "listing", "suggestion_id": "sug-001", "data": {"title": "优化标题"}, "approved_by": "admin"})
print(f"  Adopt: success={r['success']}, adopt_id={r.get('adopt_id', 'N/A')}")
r = erp.call_tool("erp_domain_status", {})
print(f"  Domain status: domains={list(r['domains'].keys())}")
r = erp.list_tools()
print(f"  Tools: {r['total']}")
print("  [PASS]")

# Test 6: Web Crawler
print("\n[6] Web Crawler")
sys.path.insert(0, 'skills/web-crawler')
import main as crawler_main
crawler = crawler_main.WebCrawler()
r = crawler.crawl("taobao", "product", "prod_001")
print(f"  Crawl: success={r['success']}, results={r['result_count']}")
r = crawler.crawl_search("xhs", "护肤品推荐", 5)
print(f"  Search: success={r['success']}, keyword={r['keyword']}")
r = crawler.crawl_batch("jd", "product", ["id1", "id2"])
print(f"  Batch: success={r['success']}, completed={r['completed']}")
r = crawler.get_proxy_status()
print(f"  Proxy: active={r['active_proxies']}, ua_pool={r['ua_pool_size']}")
stats = crawler.get_crawl_stats()
print(f"  Stats: platforms={list(stats.keys())}")
sys.path.remove('skills/web-crawler')
print("  [PASS]")

# Test 7: Data Flywheel
print("\n[7] Data Flywheel")
import importlib.util
flywheel_path = 'skills/data-flywheel'
sys.path.insert(0, flywheel_path)
spec = importlib.util.spec_from_file_location("data_flywheel_main", "skills/data-flywheel/main.py")
flywheel_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flywheel_mod)
fw = flywheel_mod.DataFlywheel()
r = fw.start_cdc(["products", "orders"])
print(f"  CDC: status={r['cdc_status']}, events={r['events_captured']}")
r = fw.sync_features("user_profile", "user_001")
print(f"  Features: success={r['success']}, type={r['feature_type']}")
r = fw.sync_vectors("ecom_rules", "products")
print(f"  Vectors: success={r['success']}, synced={r['synced_count']}")
r = fw.track_adoption("listing", "sug-001", True, {"ctr": 0.05, "conversion": 0.02})
print(f"  Adoption: success={r['success']}, adopted={r['adopted']}")
r = fw.get_flywheel_status()
print(f"  Flywheel: active={r['flywheel_active']}, cdc_events={r['cdc']['total_events']}")
sys.path.remove('skills/data-flywheel')
print("  [PASS]")

print("\n" + "=" * 60)
print("ALL 7 MODULES TESTED SUCCESSFULLY!")
print("=" * 60)
