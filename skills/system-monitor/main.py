import json
import random
from datetime import datetime, timedelta

_component_registry = {
    "gateway": {"port": 18789, "protocol": "http", "critical": True},
    "agents": {"count": 5, "names": ["main", "ecommerce", "social-media", "cs", "office"], "critical": True},
    "database": {"port": 3306, "type": "mysql", "critical": True},
    "redis": {"port": 6379, "critical": True},
    "milvus": {"port": 19530, "critical": False},
    "qdrant": {"port": 6333, "critical": False},
    "minio": {"port": 9000, "critical": False}
}

_alert_history = []

def check_component_health(component_name):
    component = _component_registry.get(component_name)
    if not component:
        return {"name": component_name, "status": "unknown", "error": "组件未注册"}

    is_healthy = random.random() > 0.05

    if is_healthy:
        status = "healthy"
        response_time = round(random.uniform(5, 150), 2)
        uptime = f"{random.randint(1, 30)}天{random.randint(0, 23)}小时"
    else:
        status = random.choice(["warning", "critical"])
        response_time = round(random.uniform(500, 3000), 2)
        uptime = f"{random.randint(0, 0)}天{random.randint(0, 2)}小时"

    result = {
        "name": component_name,
        "status": status,
        "response_time_ms": response_time,
        "uptime": uptime,
        "critical": component.get("critical", False),
        "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if component_name == "gateway":
        result["details"] = {
            "active_connections": random.randint(10, 200),
            "requests_per_minute": random.randint(50, 500),
            "success_rate": round(random.uniform(95, 99.9), 2),
            "avg_response_time": response_time
        }
    elif component_name == "agents":
        agent_statuses = {}
        for agent_name in component["names"]:
            agent_statuses[agent_name] = {
                "status": "running" if random.random() > 0.05 else "stopped",
                "memory_mb": round(random.uniform(50, 300), 1),
                "cpu_percent": round(random.uniform(5, 60), 1)
            }
        result["details"] = {"agents": agent_statuses}
    elif component_name == "database":
        result["details"] = {
            "active_connections": random.randint(5, 80),
            "max_connections": 100,
            "slow_queries": random.randint(0, 5),
            "disk_usage_percent": round(random.uniform(20, 75), 1),
            "replication_lag": random.randint(0, 2)
        }
    elif component_name == "redis":
        result["details"] = {
            "memory_used_mb": round(random.uniform(100, 800), 1),
            "memory_max_mb": 1024,
            "hit_rate": round(random.uniform(85, 99), 1),
            "connected_clients": random.randint(5, 50),
            "keys_count": random.randint(1000, 50000)
        }
    elif component_name == "milvus":
        result["details"] = {
            "collections": random.randint(3, 10),
            "total_vectors": random.randint(100000, 1000000),
            "query_latency_ms": round(random.uniform(10, 200), 2),
            "index_status": "loaded"
        }
    elif component_name == "qdrant":
        result["details"] = {
            "collections": random.randint(2, 8),
            "total_vectors": random.randint(50000, 500000),
            "query_latency_ms": round(random.uniform(10, 150), 2),
            "status": "green"
        }
    elif component_name == "minio":
        result["details"] = {
            "buckets": random.randint(3, 10),
            "total_objects": random.randint(1000, 50000),
            "storage_used_gb": round(random.uniform(10, 200), 1),
            "storage_total_gb": 500,
            "upload_success_rate": round(random.uniform(98, 99.9), 2)
        }

    return result

def check_alerts(component_results):
    alerts = []
    thresholds = {
        "gateway": {"response_time_ms": 2000, "success_rate": 95},
        "database": {"slow_queries": 10, "disk_usage_percent": 85, "active_connections_ratio": 0.8},
        "redis": {"memory_usage_percent": 80, "hit_rate": 90},
        "milvus": {"query_latency_ms": 500},
        "qdrant": {"query_latency_ms": 500},
        "minio": {"storage_usage_percent": 85}
    }

    for comp in component_results:
        name = comp["name"]
        if comp["status"] == "critical":
            alerts.append({
                "level": "critical",
                "component": name,
                "message": f"{name} 服务异常，状态：{comp['status']}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "立即检查服务状态并重启"
            })
        elif comp["status"] == "warning":
            alerts.append({
                "level": "warning",
                "component": name,
                "message": f"{name} 服务告警，响应时间：{comp['response_time_ms']}ms",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "关注服务指标，准备扩容"
            })

        details = comp.get("details", {})
        threshold = thresholds.get(name, {})

        if name == "gateway" and "success_rate" in details:
            if details["success_rate"] < threshold.get("success_rate", 95):
                alerts.append({
                    "level": "warning",
                    "component": name,
                    "message": f"Gateway成功率下降：{details['success_rate']}%",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "检查后端服务状态"
                })

        if name == "database" and "slow_queries" in details:
            if details["slow_queries"] > threshold.get("slow_queries", 10):
                alerts.append({
                    "level": "warning",
                    "component": name,
                    "message": f"MySQL慢查询过多：{details['slow_queries']}条/分钟",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "分析慢查询日志，优化SQL"
                })

        if name == "redis" and "hit_rate" in details:
            if details["hit_rate"] < threshold.get("hit_rate", 90):
                alerts.append({
                    "level": "warning",
                    "component": name,
                    "message": f"Redis命中率下降：{details['hit_rate']}%",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "检查缓存策略和热点数据"
                })

    _alert_history.extend(alerts)

    return alerts

def get_system_metrics():
    return {
        "total_requests_today": random.randint(5000, 50000),
        "avg_response_time_ms": round(random.uniform(50, 300), 2),
        "error_rate": round(random.uniform(0.1, 3.0), 2),
        "active_users": random.randint(50, 500),
        "skills_executed": random.randint(100, 2000),
        "messages_processed": random.randint(500, 5000),
        "cpu_usage_percent": round(random.uniform(20, 70), 1),
        "memory_usage_percent": round(random.uniform(40, 80), 1),
        "disk_usage_percent": round(random.uniform(30, 70), 1),
        "network_in_mb": round(random.uniform(10, 100), 1),
        "network_out_mb": round(random.uniform(20, 200), 1)
    }

def health_check(target="all"):
    if target == "all":
        targets = list(_component_registry.keys())
    else:
        targets = [target]

    component_results = []
    for t in targets:
        result = check_component_health(t)
        component_results.append(result)

    alerts = check_alerts(component_results)

    overall_status = "healthy"
    for comp in component_results:
        if comp["status"] == "critical":
            overall_status = "critical"
            break
        elif comp["status"] == "warning":
            overall_status = "warning"

    return {
        "status": overall_status,
        "components": component_results,
        "alerts": alerts,
        "metrics": get_system_metrics(),
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": f"系统状态：{overall_status}，检查{len(component_results)}个组件，发现{len(alerts)}条告警"
    }

def get_alert_history(limit=20):
    return {
        "total": len(_alert_history),
        "alerts": _alert_history[-limit:],
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def main():
    import sys
    input_data = json.load(sys.stdin)

    action = input_data.get("action", "health_check")
    target = input_data.get("target", "all")

    if action == "health_check":
        result = health_check(target)
    elif action == "alert_check":
        result = health_check(target)
        result = {"status": result["status"], "alerts": result["alerts"], "checked_at": result["checked_at"]}
    elif action == "alert_history":
        result = get_alert_history(input_data.get("limit", 20))
    elif action == "metrics":
        result = {"metrics": get_system_metrics(), "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    elif action == "component_status":
        result = check_component_health(target)
    else:
        result = health_check(target)

    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()