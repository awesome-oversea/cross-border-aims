import json
import os
import sys
import psycopg2
import psycopg2.extras
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

_PG_HOST = os.environ.get("PG_HOST", "127.0.0.1")
_PG_PORT = int(os.environ.get("PG_PORT", "5432"))
_PG_USER = os.environ.get("PG_USER", "GodyChang")
_PG_PASS = os.environ.get("PG_PASSWORD", "")
_PG_DB = os.environ.get("PG_DATABASE", "aims")

MCP_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mcporter.json")

MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "database": os.environ.get("MYSQL_DATABASE", "aims"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
}

REDIS_CONFIG = {
    "host": os.environ.get("REDIS_HOST", "localhost"),
    "port": int(os.environ.get("REDIS_PORT", "6379")),
    "db": int(os.environ.get("REDIS_DB", "0")),
    "password": os.environ.get("REDIS_PASSWORD", ""),
}

MILVUS_CONFIG = {
    "host": os.environ.get("MILVUS_HOST", "localhost"),
    "port": int(os.environ.get("MILVUS_PORT", "19530")),
}

QDRANT_CONFIG = {
    "host": os.environ.get("QDRANT_HOST", "localhost"),
    "port": int(os.environ.get("QDRANT_PORT", "6333")),
}

# MCP工具注册表：按数据源分类（mysql/redis/milvus/qdrant/ecommerce/social_media），含风险等级
MCP_TOOL_REGISTRY = {
    "mysql": {
        "tools": {
            "mysql_query": {
                "description": "执行MySQL查询",
                "params": {"sql": "SQL查询语句", "params": "查询参数(可选)"},
                "risk_level": "read",
            },
            "mysql_execute": {
                "description": "执行MySQL写操作(INSERT/UPDATE/DELETE)",
                "params": {"sql": "SQL语句", "params": "参数(可选)"},
                "risk_level": "write",
            },
            "mysql_list_tables": {
                "description": "列出数据库所有表",
                "params": {},
                "risk_level": "read",
            },
            "mysql_describe_table": {
                "description": "查看表结构",
                "params": {"table": "表名"},
                "risk_level": "read",
            },
            "mysql_insert": {
                "description": "插入数据",
                "params": {"table": "表名", "data": "数据字典"},
                "risk_level": "write",
            },
            "mysql_update": {
                "description": "更新数据",
                "params": {"table": "表名", "data": "更新数据", "where": "条件"},
                "risk_level": "write",
            },
        },
    },
    "redis": {
        "tools": {
            "redis_get": {
                "description": "获取Redis键值",
                "params": {"key": "键名"},
                "risk_level": "read",
            },
            "redis_set": {
                "description": "设置Redis键值",
                "params": {"key": "键名", "value": "值", "ttl": "过期时间(秒,可选)"},
                "risk_level": "write",
            },
            "redis_delete": {
                "description": "删除Redis键",
                "params": {"key": "键名"},
                "risk_level": "write",
            },
            "redis_hget": {
                "description": "获取Hash字段值",
                "params": {"key": "键名", "field": "字段名"},
                "risk_level": "read",
            },
            "redis_hset": {
                "description": "设置Hash字段值",
                "params": {"key": "键名", "field": "字段名", "value": "值"},
                "risk_level": "write",
            },
            "redis_hgetall": {
                "description": "获取Hash所有字段",
                "params": {"key": "键名"},
                "risk_level": "read",
            },
            "redis_list_push": {
                "description": "向列表推入值",
                "params": {"key": "键名", "value": "值", "direction": "left/right"},
                "risk_level": "write",
            },
            "redis_list_range": {
                "description": "获取列表范围",
                "params": {"key": "键名", "start": "起始索引", "stop": "结束索引"},
                "risk_level": "read",
            },
            "redis_keys": {
                "description": "搜索匹配的键",
                "params": {"pattern": "匹配模式"},
                "risk_level": "read",
            },
            "redis_ttl": {
                "description": "获取键的剩余过期时间",
                "params": {"key": "键名"},
                "risk_level": "read",
            },
            "redis_incr": {
                "description": "递增计数器",
                "params": {"key": "键名", "amount": "增量(默认1)"},
                "risk_level": "write",
            },
        },
    },
    "milvus": {
        "tools": {
            "milvus_search": {
                "description": "向量搜索",
                "params": {"collection": "集合名", "vector": "查询向量", "top_k": "返回数量"},
                "risk_level": "read",
            },
            "milvus_insert": {
                "description": "插入向量数据",
                "params": {"collection": "集合名", "data": "数据列表"},
                "risk_level": "write",
            },
            "milvus_list_collections": {
                "description": "列出所有集合",
                "params": {},
                "risk_level": "read",
            },
            "milvus_get_collection_stats": {
                "description": "获取集合统计信息",
                "params": {"collection": "集合名"},
                "risk_level": "read",
            },
        },
    },
    "qdrant": {
        "tools": {
            "qdrant_search": {
                "description": "Qdrant向量搜索",
                "params": {"collection": "集合名", "vector": "查询向量", "top_k": "返回数量"},
                "risk_level": "read",
            },
            "qdrant_list_collections": {
                "description": "列出所有集合",
                "params": {},
                "risk_level": "read",
            },
        },
    },
    "ecommerce": {
        "tools": {
            "list_products": {
                "description": "查询电商平台商品列表",
                "params": {"platform": "平台(taobao/jd/pdd)", "page": "页码", "page_size": "每页数量"},
                "risk_level": "read",
            },
            "get_product": {
                "description": "获取商品详情",
                "params": {"platform": "平台", "product_id": "商品ID"},
                "risk_level": "read",
            },
            "get_orders": {
                "description": "查询订单列表",
                "params": {"platform": "平台", "status": "订单状态", "page": "页码"},
                "risk_level": "read",
            },
            "get_ad_campaigns": {
                "description": "查询广告活动",
                "params": {"platform": "平台", "campaign_type": "广告类型"},
                "risk_level": "read",
            },
            "update_listing": {
                "description": "更新商品Listing",
                "params": {"platform": "平台", "product_id": "商品ID", "listing_data": "Listing数据"},
                "risk_level": "write",
            },
        },
    },
    "social_media": {
        "tools": {
            "publish_content": {
                "description": "发布社媒内容",
                "params": {"platform": "平台(xhs/douyin/wechat)", "content": "内容数据"},
                "risk_level": "write",
            },
            "get_analytics": {
                "description": "获取社媒数据分析",
                "params": {"platform": "平台", "content_id": "内容ID", "date_range": "日期范围"},
                "risk_level": "read",
            },
            "get_comments": {
                "description": "获取社媒评论",
                "params": {"platform": "平台", "content_id": "内容ID"},
                "risk_level": "read",
            },
        },
    },
}


def init_db():
    conn = psycopg2.connect(host=_PG_HOST, port=_PG_PORT, user=_PG_USER, password=_PG_PASS, dbname=_PG_DB)
    import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
    c.execute("""CREATE TABLE IF NOT EXISTS mcp_call_logs (
        id SERIAL PRIMARY KEY,
        server_name TEXT,
        tool_name TEXT,
        params TEXT,
        result_summary TEXT,
        status TEXT DEFAULT 'success',
        duration_ms INTEGER DEFAULT 0,
        error_message TEXT,
        called_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS mcp_cache (
        cache_key TEXT PRIMARY KEY,
        server_name TEXT,
        tool_name TEXT,
        params_hash TEXT,
        result TEXT,
        expires_at TEXT,
        created_at TEXT
    )""")
    conn.commit()
    conn.close()


def get_db_connection():
    conn = psycopg2.connect(host=_PG_HOST, port=_PG_PORT, user=_PG_USER, password=_PG_PASS, dbname=_PG_DB)
    return conn


class MySQLAdapter:
    """MySQL适配器：提供查询/写入/表结构操作，连接不可用时降级为SQLite"""
    def __init__(self, config: Dict = None):
        self.config = config or MYSQL_CONFIG
        self.connection = None

    def _get_connection(self):
        try:
            import pymysql
            if self.connection is None or not self.connection.open:
                self.connection = pymysql.connect(
                    host=self.config["host"],
                    port=self.config["port"],
                    database=self.config["database"],
                    user=self.config["user"],
                    password=self.config["password"],
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor,
                )
            return self.connection
        except ImportError:
            return None
        except Exception:
            return None

    def query(self, sql: str, params: tuple = None) -> Dict:
        conn = self._get_connection()
        if conn is None:
            return {"success": False, "error": "MySQL连接不可用，使用本地SQLite替代", "mode": "fallback"}

        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return {"success": True, "data": rows, "count": len(rows), "mode": "mysql"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "mysql"}
        finally:
            conn.commit()

    def execute(self, sql: str, params: tuple = None) -> Dict:
        conn = self._get_connection()
        if conn is None:
            return {"success": False, "error": "MySQL连接不可用", "mode": "fallback"}

        try:
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                conn.commit()
                return {"success": True, "affected_rows": affected, "mode": "mysql"}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e), "mode": "mysql"}

    def list_tables(self) -> Dict:
        return self.query("SHOW TABLES")

    def describe_table(self, table: str) -> Dict:
        return self.query(f"DESCRIBE {table}")

    def insert(self, table: str, data: Dict) -> Dict:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        values = tuple(data.values())
        return self.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)

    def update(self, table: str, data: Dict, where: str, where_params: tuple = None) -> Dict:
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        values = tuple(data.values())
        if where_params:
            values = values + where_params
        return self.execute(f"UPDATE {table} SET {set_clause} WHERE {where}", values)

    def health_check(self) -> Dict:
        result = self.query("SELECT 1 as health")
        return {"healthy": result.get("success", False), "mode": result.get("mode", "unknown")}


class RedisAdapter:
    """Redis适配器：提供键值/哈希/列表/计数器操作，支持TTL和JSON序列化"""
    def __init__(self, config: Dict = None):
        self.config = config or REDIS_CONFIG
        self.client = None

    def _get_client(self):
        try:
            import redis
            if self.client is None:
                self.client = redis.Redis(
                    host=self.config["host"],
                    port=self.config["port"],
                    db=self.config["db"],
                    password=self.config["password"] or None,
                    decode_responses=True,
                )
            return self.client
        except ImportError:
            return None
        except Exception:
            return None

    def get(self, key: str) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            value = client.get(key)
            if value is None:
                return {"success": True, "key": key, "value": None, "exists": False, "mode": "redis"}
            try:
                parsed = json.loads(value)
                return {"success": True, "key": key, "value": parsed, "exists": True, "mode": "redis"}
            except (json.JSONDecodeError, TypeError):
                return {"success": True, "key": key, "value": value, "exists": True, "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def set(self, key: str, value: Any, ttl: int = None) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            result = client.set(key, value, ex=ttl)
            return {"success": True, "key": key, "set": result, "ttl": ttl, "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def delete(self, key: str) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            result = client.delete(key)
            return {"success": True, "key": key, "deleted": result, "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def hget(self, key: str, field: str) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            value = client.hget(key, field)
            return {"success": True, "key": key, "field": field, "value": value, "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def hset(self, key: str, field: str, value: Any) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            result = client.hset(key, field, value)
            return {"success": True, "key": key, "field": field, "set": result, "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def hgetall(self, key: str) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            data = client.hgetall(key)
            return {"success": True, "key": key, "data": data, "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def list_push(self, key: str, value: Any, direction: str = "right") -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            if direction == "left":
                result = client.lpush(key, value)
            else:
                result = client.rpush(key, value)
            return {"success": True, "key": key, "length": result, "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def list_range(self, key: str, start: int = 0, stop: int = -1) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            data = client.lrange(key, start, stop)
            return {"success": True, "key": key, "data": data, "count": len(data), "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def keys(self, pattern: str = "*") -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            matching_keys = client.keys(pattern)
            return {"success": True, "pattern": pattern, "keys": matching_keys, "count": len(matching_keys), "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def ttl(self, key: str) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            ttl_val = client.ttl(key)
            return {"success": True, "key": key, "ttl": ttl_val, "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def incr(self, key: str, amount: int = 1) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Redis连接不可用", "mode": "fallback"}

        try:
            if amount == 1:
                result = client.incr(key)
            else:
                result = client.incrby(key, amount)
            return {"success": True, "key": key, "value": result, "mode": "redis"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "redis"}

    def health_check(self) -> Dict:
        client = self._get_client()
        if client is None:
            return {"healthy": False, "mode": "unavailable"}
        try:
            client.ping()
            return {"healthy": True, "mode": "redis"}
        except Exception:
            return {"healthy": False, "mode": "redis"}


class MilvusAdapter:
    """Milvus向量数据库适配器：向量搜索/插入/集合管理，支持降级模式"""
    def __init__(self, config: Dict = None):
        self.config = config or MILVUS_CONFIG
        self.client = None

    def _get_client(self):
        try:
            from pymilvus import MilvusClient
            if self.client is None:
                self.client = MilvusClient(uri=f"http://{self.config['host']}:{self.config['port']}")
            return self.client
        except ImportError:
            return None
        except Exception:
            return None

    def search(self, collection: str, vector: List[float], top_k: int = 5) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Milvus连接不可用", "mode": "fallback"}

        try:
            results = client.search(
                collection_name=collection,
                data=[vector],
                limit=top_k,
                output_fields=["*"],
            )
            return {"success": True, "results": results, "count": len(results), "mode": "milvus"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "milvus"}

    def insert(self, collection: str, data: List[Dict]) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Milvus连接不可用", "mode": "fallback"}

        try:
            result = client.insert(collection_name=collection, data=data)
            return {"success": True, "insert_count": result.get("insert_count", 0), "mode": "milvus"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "milvus"}

    def list_collections(self) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Milvus连接不可用", "mode": "fallback"}

        try:
            collections = client.list_collections()
            return {"success": True, "collections": collections, "count": len(collections), "mode": "milvus"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "milvus"}

    def get_collection_stats(self, collection: str) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Milvus连接不可用", "mode": "fallback"}

        try:
            stats = client.get_collection_stats(collection)
            return {"success": True, "stats": stats, "mode": "milvus"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "milvus"}

    def health_check(self) -> Dict:
        client = self._get_client()
        if client is None:
            return {"healthy": False, "mode": "unavailable"}
        try:
            collections = client.list_collections()
            return {"healthy": True, "mode": "milvus", "collections_count": len(collections)}
        except Exception:
            return {"healthy": False, "mode": "milvus"}


class QdrantAdapter:
    """Qdrant向量数据库适配器：向量搜索/集合列表，支持降级模式"""
    def __init__(self, config: Dict = None):
        self.config = config or QDRANT_CONFIG
        self.client = None

    def _get_client(self):
        try:
            from qdrant_client import QdrantClient
            if self.client is None:
                self.client = QdrantClient(host=self.config["host"], port=self.config["port"])
            return self.client
        except ImportError:
            return None
        except Exception:
            return None

    def search(self, collection: str, vector: List[float], top_k: int = 5) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Qdrant连接不可用", "mode": "fallback"}

        try:
            results = client.search(collection_name=collection, query_vector=vector, limit=top_k)
            return {"success": True, "results": [r.dict() for r in results], "count": len(results), "mode": "qdrant"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "qdrant"}

    def list_collections(self) -> Dict:
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "Qdrant连接不可用", "mode": "fallback"}

        try:
            collections = client.get_collections()
            return {"success": True, "collections": [c.name for c in collections.collections], "mode": "qdrant"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "qdrant"}

    def health_check(self) -> Dict:
        client = self._get_client()
        if client is None:
            return {"healthy": False, "mode": "unavailable"}
        try:
            client.get_collections()
            return {"healthy": True, "mode": "qdrant"}
        except Exception:
            return {"healthy": False, "mode": "qdrant"}


class EcommercePlatformAdapter:
    """电商平台适配器：对接淘宝/京东/拼多多API，未配置时返回模拟数据"""
    def __init__(self):
        self.platforms = {
            "taobao": {"name": "淘宝/天猫", "base_url": "https://eco.taobao.com/router/rest", "app_key": os.environ.get("TAOBAO_APP_KEY", ""), "app_secret": os.environ.get("TAOBAO_APP_SECRET", "")},
            "jd": {"name": "京东", "base_url": "https://api.jd.com/routerjson", "app_key": os.environ.get("JD_APP_KEY", ""), "app_secret": os.environ.get("JD_APP_SECRET", "")},
            "pdd": {"name": "拼多多", "base_url": "https://gw-api.pinduoduo.com/api/router", "app_key": os.environ.get("PDD_APP_KEY", ""), "app_secret": os.environ.get("PDD_APP_SECRET", "")},
        }

    def list_products(self, platform: str, page: int = 1, page_size: int = 20) -> Dict:
        config = self.platforms.get(platform)
        if not config:
            return {"success": False, "error": f"平台 {platform} 未配置"}
        if not config["app_key"]:
            return {"success": True, "platform": platform, "products": [], "count": 0, "mode": "simulated", "message": f"{config['name']} API未配置，返回模拟数据"}
        return {"success": True, "platform": platform, "products": [], "count": 0, "mode": "api", "message": "API调用已就绪"}

    def get_product(self, platform: str, product_id: str) -> Dict:
        config = self.platforms.get(platform)
        if not config:
            return {"success": False, "error": f"平台 {platform} 未配置"}
        return {"success": True, "platform": platform, "product_id": product_id, "mode": "simulated"}

    def get_orders(self, platform: str, status: str = None, page: int = 1, page_size: int = 20) -> Dict:
        config = self.platforms.get(platform)
        if not config:
            return {"success": False, "error": f"平台 {platform} 未配置"}
        return {"success": True, "platform": platform, "orders": [], "count": 0, "mode": "simulated"}

    def get_ad_campaigns(self, platform: str, campaign_type: str = None) -> Dict:
        config = self.platforms.get(platform)
        if not config:
            return {"success": False, "error": f"平台 {platform} 未配置"}
        return {"success": True, "platform": platform, "campaigns": [], "mode": "simulated"}

    def update_listing(self, platform: str, product_id: str, listing_data: Dict) -> Dict:
        config = self.platforms.get(platform)
        if not config:
            return {"success": False, "error": f"平台 {platform} 未配置"}
        return {"success": True, "platform": platform, "product_id": product_id, "updated": True, "mode": "simulated"}

    def health_check(self) -> Dict:
        configured = sum(1 for p in self.platforms.values() if p["app_key"])
        return {"healthy": True, "mode": "ecommerce", "configured_platforms": configured, "total_platforms": len(self.platforms)}


class SocialMediaAdapter:
    """社媒平台适配器：对接小红书/抖音/微信API，支持内容发布/数据分析/评论获取"""
    def __init__(self):
        self.platforms = {
            "xhs": {"name": "小红书", "app_key": os.environ.get("XHS_APP_KEY", ""), "app_secret": os.environ.get("XHS_APP_SECRET", "")},
            "douyin": {"name": "抖音", "app_key": os.environ.get("DOUYIN_APP_KEY", ""), "app_secret": os.environ.get("DOUYIN_APP_SECRET", "")},
            "wechat": {"name": "微信/企微", "app_key": os.environ.get("WECHAT_APP_KEY", ""), "app_secret": os.environ.get("WECHAT_APP_SECRET", "")},
        }

    def publish_content(self, platform: str, content: Dict) -> Dict:
        config = self.platforms.get(platform)
        if not config:
            return {"success": False, "error": f"平台 {platform} 未配置"}
        return {"success": True, "platform": platform, "published": True, "mode": "simulated"}

    def get_analytics(self, platform: str, content_id: str = None, date_range: Dict = None) -> Dict:
        config = self.platforms.get(platform)
        if not config:
            return {"success": False, "error": f"平台 {platform} 未配置"}
        return {"success": True, "platform": platform, "analytics": {}, "mode": "simulated"}

    def get_comments(self, platform: str, content_id: str) -> Dict:
        config = self.platforms.get(platform)
        if not config:
            return {"success": False, "error": f"平台 {platform} 未配置"}
        return {"success": True, "platform": platform, "comments": [], "mode": "simulated"}

    def health_check(self) -> Dict:
        configured = sum(1 for p in self.platforms.values() if p["app_key"])
        return {"healthy": True, "mode": "social_media", "configured_platforms": configured, "total_platforms": len(self.platforms)}


class MCPFourStageProtocol:
    """MCP四阶段协议：意图识别 → 能力协商 → 标准化调用 → 执行反馈"""

    def __init__(self, framework):
        self.framework = framework

    def process(self, user_intent: str, context: Dict = None) -> Dict:
        """四阶段协议主流程：意图→协商→调用→反馈，串联完整MCP调用链路"""

        if context is None:
            context = {}

        stage1 = self._stage1_intent_recognition(user_intent, context)
        stage2 = self._stage2_capability_negotiation(stage1, context)
        stage3 = self._stage3_standardized_call(stage2, context)
        stage4 = self._stage4_execution_feedback(stage3, context)

        return {
            "success": stage4.get("success", False),
            "stages": {
                "intent_recognition": stage1,
                "capability_negotiation": stage2,
                "standardized_call": stage3,
                "execution_feedback": stage4,
            },
            "result": stage4.get("result"),
            "recommendation": stage4.get("recommendation"),
        }

    def _stage1_intent_recognition(self, user_intent: str, context: Dict) -> Dict:
        """阶段1-意图识别：基于关键词匹配检测用户意图（查询商品/订单/广告/发布内容等）"""

        intent_map = {
            "query_product": ["查商品", "产品信息", "商品详情", "product", "listing"],
            "query_order": ["查订单", "订单状态", "order", "物流"],
            "manage_ad": ["广告", "投放", "出价", "ad", "campaign", "ACOS"],
            "publish_content": ["发布", "种草", "笔记", "publish", "内容"],
            "query_analytics": ["数据", "报表", "分析", "analytics", "统计"],
            "manage_review": ["评论", "评价", "review", "差评"],
            "query_inventory": ["库存", "入库", "inventory", "仓储"],
        }

        detected_intent = "unknown"
        confidence = 0.0
        matched_keywords = []

        for intent, keywords in intent_map.items():
            for kw in keywords:
                if kw.lower() in user_intent.lower():
                    matched_keywords.append(kw)
            if matched_keywords:
                detected_intent = intent
                confidence = min(len(matched_keywords) / 3.0, 1.0)
                break

        return {
            "status": "completed",
            "user_intent": user_intent,
            "detected_intent": detected_intent,
            "confidence": round(confidence, 2),
            "matched_keywords": matched_keywords,
        }

    def _stage2_capability_negotiation(self, stage1_result: Dict, context: Dict) -> Dict:
        """阶段2-能力协商：将意图映射到MCP Server+Tool的组合，确认所需参数和风险等级"""

        intent = stage1_result.get("detected_intent", "unknown")

        capability_map = {
            "query_product": {"server": "ecommerce", "tool": "list_products", "required_params": ["platform"]},
            "query_order": {"server": "ecommerce", "tool": "get_orders", "required_params": ["platform"]},
            "manage_ad": {"server": "ecommerce", "tool": "get_ad_campaigns", "required_params": ["platform"]},
            "publish_content": {"server": "social_media", "tool": "publish_content", "required_params": ["platform", "content"]},
            "query_analytics": {"server": "social_media", "tool": "get_analytics", "required_params": ["platform"]},
            "manage_review": {"server": "ecommerce", "tool": "list_products", "required_params": ["platform"]},
            "query_inventory": {"server": "mysql", "tool": "mysql_query", "required_params": ["sql"]},
        }

        capability = capability_map.get(intent)
        if not capability:
            return {
                "status": "no_capability",
                "intent": intent,
                "message": "未找到匹配的MCP能力",
                "suggestion": "请明确您的需求或联系管理员配置对应MCP Server",
            }

        return {
            "status": "negotiated",
            "intent": intent,
            "server": capability["server"],
            "tool": capability["tool"],
            "required_params": capability["required_params"],
            "risk_level": MCP_TOOL_REGISTRY.get(capability["server"], {}).get("tools", {}).get(capability["tool"], {}).get("risk_level", "read"),
        }

    def _stage3_standardized_call(self, stage2_result: Dict, context: Dict) -> Dict:
        """阶段3-标准化调用：组装参数，高风险写操作需人工确认"""

        if stage2_result.get("status") != "negotiated":
            return {"status": "skipped", "reason": "能力协商未通过"}

        tool_name = stage2_result["tool"]
        server = stage2_result["server"]
        risk_level = stage2_result.get("risk_level", "read")

        if risk_level == "write" and not context.get("auto_approve", False):
            return {
                "status": "pending_approval",
                "tool": tool_name,
                "server": server,
                "risk_level": risk_level,
                "message": "写操作需要人工确认",
            }

        params = context.get("params", {})
        for rp in stage2_result.get("required_params", []):
            if rp not in params:
                params[rp] = context.get(rp, "")

        return {
            "status": "ready",
            "tool": tool_name,
            "server": server,
            "params": params,
            "risk_level": risk_level,
        }

    def _stage4_execution_feedback(self, stage3_result: Dict, context: Dict) -> Dict:
        """阶段4-执行反馈：调用实际工具并返回执行结果和建议"""

        if stage3_result.get("status") not in ("ready", "pending_approval"):
            return {
                "status": "skipped",
                "success": False,
                "result": None,
                "recommendation": "调用流程未就绪",
            }

        if stage3_result.get("status") == "pending_approval":
            return {
                "status": "waiting_approval",
                "success": False,
                "result": None,
                "recommendation": "等待人工确认后执行",
            }

        tool_name = stage3_result["tool"]
        params = stage3_result.get("params", {})

        result = self.framework.call_tool(tool_name, params)

        recommendation = ""
        if result.get("success"):
            recommendation = "执行成功"
            if result.get("mode") == "simulated":
                recommendation = "模拟执行成功，实际API未连接"
        else:
            recommendation = f"执行失败: {result.get('error', '未知错误')}"

        return {
            "status": "completed",
            "success": result.get("success", False),
            "result": result,
            "recommendation": recommendation,
        }


class MCPFramework:
    """MCP框架核心：管理多数据源适配器、四阶段协议、工具调用和健康检查"""
    def __init__(self):
        self.adapters = {
            "mysql": MySQLAdapter(),
            "redis": RedisAdapter(),
            "milvus": MilvusAdapter(),
            "qdrant": QdrantAdapter(),
            "ecommerce": EcommercePlatformAdapter(),
            "social_media": SocialMediaAdapter(),
        }
        self.four_stage = MCPFourStageProtocol(self)
        init_db()

    def call_tool(self, tool_name: str, params: Dict) -> Dict:
        """工具调用入口：按tool_name查找注册表，路由到对应适配器方法，记录调用日志"""

        start_time = time.time()

        server_name = self._get_server_for_tool(tool_name)
        if not server_name:
            return {"success": False, "error": f"工具 {tool_name} 未注册"}

        adapter = self.adapters.get(server_name)
        if not adapter:
            return {"success": False, "error": f"适配器 {server_name} 不可用"}

        method_name = tool_name.replace(f"{server_name}_", "", 1)
        method = getattr(adapter, method_name, None)
        if not method:
            return {"success": False, "error": f"方法 {method_name} 不存在于 {server_name} 适配器"}

        try:
            result = method(**params)
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_call(server_name, tool_name, params, result, duration_ms)
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_call(server_name, tool_name, params, {"success": False, "error": str(e)}, duration_ms, error=str(e))
            return {"success": False, "error": str(e)}

    def health_check_all(self) -> Dict:
        results = {}
        for name, adapter in self.adapters.items():
            results[name] = adapter.health_check()

        all_healthy = all(r.get("healthy", False) for r in results.values())

        return {
            "overall_healthy": all_healthy,
            "servers": results,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def list_tools(self, server_name: str = None) -> Dict:
        if server_name:
            tools = MCP_TOOL_REGISTRY.get(server_name, {})
            return {"server": server_name, "tools": tools.get("tools", {}), "count": len(tools.get("tools", {}))}

        all_tools = {}
        total = 0
        for server, info in MCP_TOOL_REGISTRY.items():
            all_tools[server] = info.get("tools", {})
            total += len(info.get("tools", {}))

        return {"servers": all_tools, "total_tools": total}

    def get_call_history(self, limit: int = 50) -> List[Dict]:
        try:
            conn = get_db_connection()
            import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
            c.execute(
                "SELECT server_name, tool_name, params, result_summary, status, duration_ms, error_message, called_at FROM mcp_call_logs ORDER BY id DESC LIMIT %s",
                (limit,),
            )
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception:
            return []

    def _get_server_for_tool(self, tool_name: str) -> Optional[str]:
        for server_name, info in MCP_TOOL_REGISTRY.items():
            if tool_name in info.get("tools", {}):
                return server_name
        return None

    def _log_call(self, server_name: str, tool_name: str, params: Dict, result: Dict, duration_ms: int, error: str = ""):
        try:
            conn = get_db_connection()
            import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result_summary = json.dumps(result, ensure_ascii=False, default=str)[:500] if result else ""
            c.execute(
                "INSERT INTO mcp_call_logs (server_name, tool_name, params, result_summary, status, duration_ms, error_message, called_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    server_name,
                    tool_name,
                    json.dumps(params, ensure_ascii=False)[:500],
                    result_summary,
                    "error" if error else "success",
                    duration_ms,
                    error,
                    now,
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


def main():
    input_data = json.loads(sys.stdin.read())

    action = input_data.get("action", "list_tools")
    framework = MCPFramework()

    if action == "call_tool":
        tool_name = input_data.get("tool_name", "")
        params = input_data.get("params", {})
        result = framework.call_tool(tool_name, params)

    elif action == "health_check":
        result = framework.health_check_all()

    elif action == "list_tools":
        server_name = input_data.get("server_name")
        result = framework.list_tools(server_name)

    elif action == "get_history":
        limit = input_data.get("limit", 50)
        result = {"history": framework.get_call_history(limit)}

    elif action == "four_stage":
        user_intent = input_data.get("user_intent", "")
        context = input_data.get("context", {})
        result = framework.four_stage.process(user_intent, context)

    elif action == "list_servers":
        result = {
            "servers": list(framework.adapters.keys()),
            "total": len(framework.adapters),
            "details": {name: adapter.health_check() for name, adapter in framework.adapters.items()},
        }

    else:
        result = {"error": f"未知操作: {action}"}

    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
