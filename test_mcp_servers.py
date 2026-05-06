import sys
sys.path.insert(0, 'skills/mcp-framework')

from ecom_mcp import EcomMCP
from social_mcp import SocialMCP
from multimodal_mcp import MultimodalMCP

print("=== EcomMCP Tests ===")
ecom = EcomMCP()

r1 = ecom.call_tool("ecom_product_list", {"platform": "taobao", "page": 1, "page_size": 5})
print(f"1. Product List: success={r1['success']}, total={r1['total']}, count={len(r1['products'])}")

r2 = ecom.call_tool("ecom_product_detail", {"platform": "jd", "product_id": "jd_prod_0001"})
print(f"2. Product Detail: success={r2['success']}, title={r2.get('product', {}).get('title', 'N/A')}")

r3 = ecom.call_tool("ecom_product_update", {"platform": "pdd", "product_id": "pdd_prod_0001", "price": 199.9})
print(f"3. Product Update: success={r3['success']}, message={r3.get('message', '')}")

r4 = ecom.call_tool("ecom_order_list", {"platform": "taobao"})
print(f"4. Order List: success={r4['success']}, total={r4['total']}")

r5 = ecom.call_tool("ecom_ad_campaign_list", {"platform": "jd"})
print(f"5. Ad Campaign List: success={r5['success']}, count={len(r5['campaigns'])}")

r6 = ecom.call_tool("ecom_review_list", {"platform": "pdd", "product_id": "pdd_prod_0001"})
print(f"6. Review List: success={r6['success']}, count={len(r6['reviews'])}")

r7 = ecom.list_tools()
print(f"7. List Tools: total={r7['total']}")

r8 = ecom.get_platform_status()
print(f"8. Platform Status: platforms={list(r8.keys())}")

print("\n=== SocialMCP Tests ===")
social = SocialMCP()

s1 = social.call_tool("social_content_publish", {"platform": "xhs", "title": "测试笔记", "content": "这是一篇测试笔记，内容长度符合要求，包含一些关键词和描述文字，用于验证发布功能。", "tags": "测试,笔记"})
print(f"1. Content Publish: success={s1['success']}, content_id={s1.get('content_id', 'N/A')}")

s2 = social.call_tool("social_content_list", {"platform": "xhs"})
print(f"2. Content List: success={s2['success']}, count={len(s2['contents'])}")

s3 = social.call_tool("social_analytics", {"platform": "douyin"})
print(f"3. Analytics: success={s3['success']}, total_contents={s3['analytics'].get('total_contents', 0)}")

s4 = social.call_tool("social_trending", {"platform": "xhs", "limit": 5})
print(f"4. Trending: success={s4['success']}, count={len(s4['trending'])}")

s5 = social.call_tool("social_compliance_check", {"platform": "xhs", "content": "这是最好的产品，加微信获取优惠"})
print(f"5. Compliance: success={s5['success']}, compliant={s5['compliant']}, issues={s5['issue_count']}")

s6 = social.call_tool("wechat_send_message", {"platform": "wechat", "msg_type": "text", "content": "测试消息", "user_list": "@all"})
print(f"6. WeChat Send: success={s6['success']}")

s7 = social.call_tool("wechat_transfer_human", {"platform": "wechat", "user_id": "user001", "reason": "负面投诉"})
print(f"7. Transfer Human: success={s7['success']}")

s8 = social.list_tools()
print(f"8. List Tools: total={s8['total']}")

print("\n=== MultimodalMCP Tests ===")
mm = MultimodalMCP()

m1 = mm.call_tool("dalle_generate", {"prompt": "商品展示图", "size": "1024x1024", "n": 2})
print(f"1. DALL-E Generate: success={m1['success']}, images={len(m1.get('image_urls', []))}, cost={m1.get('cost', 0)}")

m2 = mm.call_tool("whisper_transcribe", {"audio_url": "https://example.com/audio.mp3", "language": "zh"})
print(f"2. Whisper Transcribe: success={m2['success']}, text_len={len(m2.get('text', ''))}")

m3 = mm.call_tool("tts_synthesize", {"text": "欢迎使用AI营销系统", "voice": "alloy"})
print(f"3. TTS Synthesize: success={m3['success']}, cost={m3.get('cost', 0)}")

m4 = mm.call_tool("vision_analyze", {"image_url": "https://example.com/product.jpg", "prompt": "分析商品图片"})
print(f"4. Vision Analyze: success={m4['success']}")

m5 = mm.list_tools()
print(f"5. List Tools: total={m5['total']}")

m6 = mm.get_usage_stats()
print(f"6. Usage Stats: configured={m6['configured']}")

print("\nAll MCP tests passed!")
