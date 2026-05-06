import sys

sys.path.insert(0, "skills/agent-orchestrator")
from main import AgentOrchestrator


def assert_has_skill(result, expected_skill):
    skills = [item["name"] for item in result["decision"]["skill_plan"]["skills"]]
    assert expected_skill in skills, f"expected skill {expected_skill}, got {skills}"


def assert_agent(result, expected_agent):
    actual = result["decision"]["agent_routing"]["agent_id"]
    assert actual == expected_agent, f"expected agent {expected_agent}, got {actual}"


def assert_workflow(result, expected_workflow):
    workflow = result["decision"]["skill_plan"].get("workflow", {})
    actual = workflow.get("name")
    assert actual == expected_workflow, f"expected workflow {expected_workflow}, got {actual}"


def analyze(orchestrator, message, context):
    context = dict(context)
    context["skip_rag"] = True
    perception = orchestrator.perception.process(message, context)
    decision = orchestrator.decision.process(perception, context)
    return {
        "perception": perception,
        "decision": decision,
    }


def main():
    orchestrator = AgentOrchestrator()

    report_result = analyze(
        orchestrator,
        "帮我整理一份本周经营周报。",
        {"user_id": "ops001", "channel": "feishu"},
    )
    assert report_result["perception"]["intent"]["intent"] == "report_generation"
    assert_agent(report_result, "office")
    assert_has_skill(report_result, "report-gen")

    video_result = analyze(
        orchestrator,
        "给视频号写一个适合家庭清洁喷雾的分发脚本。",
        {"user_id": "social001", "channel": "feishu"},
    )
    assert video_result["perception"]["intent"]["intent"] in ["video_channel_script", "video_channel_distribution"]
    assert_agent(video_result, "social-media")
    assert_has_skill(video_result, "video-channel")

    email_result = analyze(
        orchestrator,
        "帮我起草一封给渠道商的报价邮件。",
        {
            "user_id": "office001",
            "channel": "feishu",
            "subject": "新品渠道报价沟通",
            "body": "客户想了解夏季风扇的批量采购价格和交期。",
        },
    )
    assert email_result["perception"]["intent"]["intent"] == "email_management"
    assert_agent(email_result, "office")
    assert_has_skill(email_result, "email-mgr")

    doc_result = analyze(
        orchestrator,
        "把这次项目复盘整理成会议纪要。",
        {
            "user_id": "office002",
            "channel": "feishu",
            "document_type": "meeting_minutes",
            "content": "会议围绕618投放复盘、客服响应优化和下周计划展开。",
        },
    )
    assert doc_result["perception"]["intent"]["intent"] == "meeting_minutes"
    assert_agent(doc_result, "office")
    assert_has_skill(doc_result, "doc-auto")

    cs_result = analyze(
        orchestrator,
        "我要投诉，你们处理太慢了，我非常不满，赶紧退款。",
        {"user_id": "cs001", "channel": "wework", "customer_tier": "VIP", "order_value": 6888},
    )
    assert cs_result["perception"]["intent"]["intent"] in ["refund", "complaint", "aftersale"]
    assert_agent(cs_result, "cs")
    assert_has_skill(cs_result, "sentiment-analysis")

    office_workflow = analyze(
        orchestrator,
        "把本周经营周报整理出来，补一版图表，再起草同步邮件和文档摘要。",
        {"user_id": "ops002", "channel": "feishu", "subject": "本周经营复盘"},
    )
    assert_agent(office_workflow, "office")
    assert_has_skill(office_workflow, "skill-orchestrator")
    assert_workflow(office_workflow, "office_productivity_suite")

    social_workflow = analyze(
        orchestrator,
        "围绕厨房清洁喷雾做一版小红书、抖音和视频号内容，再补一个私域导流方案。",
        {
            "user_id": "social002",
            "channel": "feishu",
            "product_name": "厨房清洁喷雾",
            "targetPlatform": "video-channel",
            "sourcePlatform": "xiaohongshu",
        },
    )
    assert_agent(social_workflow, "social-media")
    assert_has_skill(social_workflow, "skill-orchestrator")
    assert_workflow(social_workflow, "social_media_content_flywheel")

    cs_workflow = analyze(
        orchestrator,
        "订单号JD2026042100123，单号SF123456789012，帮我查物流并处理退款投诉。",
        {
            "user_id": "cs002",
            "channel": "wework",
            "customer_tier": "VIP",
            "order_value": 6999,
        },
    )
    assert_agent(cs_workflow, "cs")
    assert_has_skill(cs_workflow, "skill-orchestrator")
    assert_workflow(cs_workflow, "customer_service_resolution")

    ecommerce_workflow = analyze(
        orchestrator,
        "给这款露营灯做 listing、广告优化和经营看板。",
        {
            "user_id": "ecom002",
            "channel": "feishu",
            "product_name": "Rechargeable Camping Lantern",
            "platform": "amazon",
            "metrics": {"acos": 31, "ctr": 0.7, "cvr": 8.5, "roas": 3.2},
        },
    )
    assert_agent(ecommerce_workflow, "ecommerce")
    assert_has_skill(ecommerce_workflow, "skill-orchestrator")
    assert_workflow(ecommerce_workflow, "ecommerce_operation_hub")

    print("business capability checks passed")


if __name__ == "__main__":
    main()
