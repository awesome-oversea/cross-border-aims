import json
from datetime import datetime

_user_profiles = {}

def get_profile(user_id):
    if user_id in _user_profiles:
        return _user_profiles[user_id]

    default_profile = {
        "user_id": user_id,
        "name": f"用户{user_id[-4:]}",
        "phone": "",
        "tier": "普通",
        "tags": [],
        "preferences": {
            "categories": [],
            "price_range": "",
            "brands": []
        },
        "interaction_count": 0,
        "last_interaction": "",
        "satisfaction_history": [],
        "complaint_count": 0,
        "total_orders": 0,
        "total_spend": 0.0,
        "avg_order_value": 0.0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return default_profile

def create_profile(user_id, name, phone="", tier="普通"):
    if user_id in _user_profiles:
        return {"success": False, "message": f"用户 {user_id} 已存在"}

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    profile = {
        "user_id": user_id,
        "name": name,
        "phone": phone,
        "tier": tier,
        "tags": [],
        "preferences": {
            "categories": [],
            "price_range": "",
            "brands": []
        },
        "interaction_count": 0,
        "last_interaction": "",
        "satisfaction_history": [],
        "complaint_count": 0,
        "total_orders": 0,
        "total_spend": 0.0,
        "avg_order_value": 0.0,
        "created_at": now,
        "updated_at": now
    }

    _user_profiles[user_id] = profile

    tier_tags = {
        "VIP": ["高价值", "VIP用户"],
        "银卡": ["中价值", "银卡用户"],
        "普通": ["普通用户"]
    }
    profile["tags"] = tier_tags.get(tier, ["普通用户"])

    return {"success": True, "user_profile": profile, "message": f"用户 {name} 的画像已创建"}

def update_profile(user_id, data):
    profile = get_profile(user_id)

    if profile["created_at"] == "":
        return {"success": False, "message": f"用户 {user_id} 不存在"}

    if "name" in data:
        profile["name"] = data["name"]
    if "phone" in data:
        profile["phone"] = data["phone"]
    if "tier" in data:
        profile["tier"] = data["tier"]
    if "preferences" in data:
        profile["preferences"].update(data["preferences"])
    if "tags" in data:
        profile["tags"] = data["tags"]
    if "total_orders" in data:
        profile["total_orders"] = data["total_orders"]
    if "total_spend" in data:
        profile["total_spend"] = data["total_spend"]
        if profile["total_orders"] > 0:
            profile["avg_order_value"] = profile["total_spend"] / profile["total_orders"]

    profile["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {"success": True, "user_profile": profile, "message": "画像已更新"}

def add_tag(user_id, tag):
    profile = get_profile(user_id)

    if profile["created_at"] == "":
        return {"success": False, "message": f"用户 {user_id} 不存在"}

    if tag not in profile["tags"]:
        profile["tags"].append(tag)
        profile["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {"success": True, "user_profile": profile, "message": f"已添加标签: {tag}"}

def remove_tag(user_id, tag):
    profile = get_profile(user_id)

    if profile["created_at"] == "":
        return {"success": False, "message": f"用户 {user_id} 不存在"}

    if tag in profile["tags"]:
        profile["tags"].remove(tag)
        profile["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {"success": True, "user_profile": profile, "message": f"已移除标签: {tag}"}

def record_interaction(user_id, interaction_type, content="", sentiment="neutral", satisfaction=0):
    profile = get_profile(user_id)

    if profile["created_at"] == "":
        profile["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    profile["interaction_count"] += 1
    profile["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if satisfaction > 0:
        profile["satisfaction_history"].append(satisfaction)
        if len(profile["satisfaction_history"]) > 10:
            profile["satisfaction_history"] = profile["satisfaction_history"][-10:]

    if interaction_type == "complaint":
        profile["complaint_count"] += 1
        if "投诉风险" not in profile["tags"]:
            profile["tags"].append("投诉风险")

    if sentiment == "positive" and "满意用户" not in profile["tags"]:
        if "投诉风险" in profile["tags"]:
            profile["tags"].remove("投诉风险")
        if "满意用户" not in profile["tags"]:
            profile["tags"].append("满意用户")

    if profile["interaction_count"] > 10 and "活跃用户" not in profile["tags"]:
        profile["tags"].append("活跃用户")

    profile["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    interaction_record = {
        "timestamp": profile["last_interaction"],
        "type": interaction_type,
        "content": content[:100] if content else "",
        "sentiment": sentiment,
        "satisfaction": satisfaction
    }

    return {
        "success": True,
        "user_profile": profile,
        "interaction_record": interaction_record,
        "message": f"已记录 {interaction_type} 类型的交互"
    }

def process_request(user_id, action, data=None):
    if data is None:
        data = {}

    if action == "get":
        profile = get_profile(user_id)
        if profile["created_at"] == "":
            return {"success": False, "message": f"用户 {user_id} 不存在"}
        return {"success": True, "user_profile": profile}

    elif action == "create":
        return create_profile(
            user_id,
            data.get("name", f"用户{user_id[-4:]}"),
            data.get("phone", ""),
            data.get("tier", "普通")
        )

    elif action == "update":
        return update_profile(user_id, data)

    elif action == "add_tag":
        tag = data.get("tag", "")
        if not tag:
            return {"success": False, "message": "标签不能为空"}
        return add_tag(user_id, tag)

    elif action == "remove_tag":
        tag = data.get("tag", "")
        if not tag:
            return {"success": False, "message": "标签不能为空"}
        return remove_tag(user_id, tag)

    elif action == "record_interaction":
        return record_interaction(
            user_id,
            data.get("interaction_type", "general"),
            data.get("content", ""),
            data.get("sentiment", "neutral"),
            data.get("satisfaction", 0)
        )

    else:
        return {"success": False, "message": f"未知操作: {action}"}

def main():
    import sys
    input_data = json.load(sys.stdin)

    user_id = input_data.get("user_id", "")
    action = input_data.get("action", "get")
    data = input_data.get("data", {})

    if not user_id:
        print(json.dumps({"success": False, "message": "user_id不能为空"}))
        return

    result = process_request(user_id, action, data)

    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()