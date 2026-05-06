import sys

sys.path.insert(0, "skills/skill-orchestrator")
from main import WorkflowEngine


def assert_step_success(result, output_key):
    step = result["step_results"].get(output_key, {})
    assert step.get("success"), f"{output_key} failed: {step}"


def assert_workflow_registered(workflows, name):
    built_in = {item["name"]: item for item in workflows["built_in"]}
    assert name in built_in, f"workflow {name} not found"
    return built_in[name]


def main():
    engine = WorkflowEngine()

    workflows = engine.list_workflows()
    assert workflows["total"] >= 9, workflows
    assert_workflow_registered(workflows, "ecommerce_operation_hub")
    assert_workflow_registered(workflows, "social_media_content_flywheel")
    assert_workflow_registered(workflows, "customer_service_resolution")
    assert_workflow_registered(workflows, "office_productivity_suite")

    ecommerce = engine.execute_workflow(
        "ecommerce_operation_hub",
        {
            "platform": "amazon",
            "product_name": "Rechargeable Camping Lantern",
            "category": "electronics",
            "selling_points": ["10000mAh battery", "IPX5 waterproof", "camping and emergency ready"],
            "material_type": "main_image",
            "audience": "outdoor users",
            "metrics": {"acos": 32, "ctr": 0.8, "cvr": 9.5, "roas": 3.1, "spend": 180, "revenue": 560},
            "campaign_type": "sp",
            "report_type": "weekly",
            "date": "2026-04-28",
        },
        {"user_id": "ecom-001", "channel": "feishu"},
    )
    assert ecommerce["success"], ecommerce
    assert ecommerce["aggregated_result"]["type"] == "ecommerce_operations_report"
    assert_step_success(ecommerce, "listing")
    assert_step_success(ecommerce, "materials")
    assert_step_success(ecommerce, "ad_analysis")
    assert_step_success(ecommerce, "report")
    assert_step_success(ecommerce, "chart_board")

    social = engine.execute_workflow(
        "social_media_content_flywheel",
        {
            "product_name": "厨房去油污清洁喷雾",
            "selling_points": ["去油快", "不刺鼻", "台面和灶台都能用"],
            "audience": "家庭主理人",
            "target_audience": "家庭主理人",
            "sourcePlatform": "xiaohongshu",
            "targetPlatform": "video-channel",
            "duration": 45,
            "video_type": "product",
        },
        {"user_id": "social-001", "channel": "feishu"},
    )
    assert social["success"], social
    assert social["aggregated_result"]["type"] == "social_media_flywheel_report"
    assert_step_success(social, "xhs_content")
    assert_step_success(social, "douyin_script")
    assert_step_success(social, "video_channel_content")
    assert_step_success(social, "drain_strategy")
    assert_step_success(social, "opinion")

    customer_service = engine.execute_workflow(
        "customer_service_resolution",
        {
            "user_message": "我要投诉，订单号 JD2026042100123 的物流太慢了，单号 SF123456789012，到现在还没到，赶紧给我处理。",
            "history": [
                {"role": "user", "content": "昨天说会回复我，到现在还没消息", "sentiment": "negative"}
            ],
            "order_id": "JD2026042100123",
            "tracking_number": "SF123456789012",
            "platform": "jd",
        },
        {"user_id": "cs-001", "channel": "wework", "customer_tier": "VIP", "order_value": 6899},
    )
    assert customer_service["success"], customer_service
    assert customer_service["aggregated_result"]["type"] == "customer_service_report"
    assert_step_success(customer_service, "intent")
    assert_step_success(customer_service, "order")
    assert_step_success(customer_service, "logistics")
    assert_step_success(customer_service, "aftersale")
    assert_step_success(customer_service, "sentiment")

    office = engine.execute_workflow(
        "office_productivity_suite",
        {
            "report_type": "weekly",
            "date": "2026-04-28",
            "platform": "all",
        },
        {"user_id": "office-001", "channel": "feishu"},
    )
    assert office["success"], office
    assert office["aggregated_result"]["type"] == "office_productivity_report"
    assert_step_success(office, "report")
    assert_step_success(office, "chart_board")
    assert_step_success(office, "document")
    assert_step_success(office, "email")

    print("skill orchestrator business workflows passed")


if __name__ == "__main__":
    main()
