import json
import os
import sys
from typing import Dict, List, Any
import hashlib, random

_EMBED_CACHE = {}
def _embed(text: str, dim: int = 768) -> list:
    """Try Ollama embedding, fallback to pseudo."""
    if text in _EMBED_CACHE:
        return _EMBED_CACHE[text]
    try:
        import json, urllib.request
        host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        data = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
        req = urllib.request.Request(f"{host}/api/embeddings", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            vec = json.loads(resp.read()).get("embedding")
            if vec and len(vec) == dim:
                _EMBED_CACHE[text] = vec
                return vec
    except Exception:
        pass
    # Fallback: deterministic pseudo-embedding
    h = hashlib.sha256(text.encode('utf-8')).digest()
    rng = random.Random(h)
    vec = [rng.random() for _ in range(dim)]
    norm = sum(x*x for x in vec) ** 0.5
    vec = [x/norm for x in vec]
    _EMBED_CACHE[text] = vec
    return vec

MILVUS_HOST = os.environ.get("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.environ.get("MILVUS_PORT", "19530"))
VECTOR_DIM = 384

# RAG知识库模拟数据：ACOS优化/Listing优化/物流选择/产品合规/客服标准
SIMULATED_DATA = [
    {
        "title": "亚马逊广告ACOS优化策略",
        "content": "ACOS（广告销售成本比）是衡量亚马逊广告效果的关键指标。优化ACOS的策略包括：1) 优化关键词出价，降低无效点击花费；2) 优化产品Listing，提高转化率；3) 定期清理表现差的关键词；4) 利用否定关键词排除无效流量。建议ACOS目标值控制在25%-35%之间。",
        "category": "ad-optimizer",
        "source": "电商知识库"
    },
    {
        "title": "亚马逊Listing优化指南",
        "content": "优化亚马逊Listing需要关注以下几点：1) 标题应包含主要关键词，长度控制在60-80字符；2) 五点描述突出产品核心卖点；3) 产品描述详细说明产品特性和使用场景；4) 使用高质量图片和视频；5) 合理使用A+页面增强转化。",
        "category": "listing-gen",
        "source": "电商知识库"
    },
    {
        "title": "跨境电商物流选择指南",
        "content": "跨境电商物流主要有以下几种选择：1) FBA（亚马逊物流）：快速可靠，但成本较高；2) 自发货：成本低，但时效慢；3) 海外仓：平衡成本和时效；4) 专线物流：特定国家的专线服务。选择时需考虑产品特性、目的地国家和预算。",
        "category": "logistics",
        "source": "电商知识库"
    },
    {
        "title": "产品合规要求",
        "content": "跨境电商产品需符合目标市场的合规要求：1) 欧盟市场需CE认证；2) 美国市场需FDA认证（针对特定产品）；3) 产品标签需包含必要信息；4) 电子产品需符合安全标准。建议在发货前确认所有合规要求。",
        "category": "compliance",
        "source": "电商知识库"
    },
    {
        "title": "客服响应时间标准",
        "content": "良好的客服响应时间是提升客户满意度的关键：1) 售前咨询应在2小时内响应；2) 售后问题应在24小时内处理；3) 物流查询应在12小时内回复；4) 高优先级问题需即时响应。建议设置自动回复告知客户响应时间。",
        "category": "cs",
        "source": "电商知识库"
    }
]

class ECommerceRAG:
    """电商RAG检索器：优先连接Milvus向量库，不可用时降级为模拟文本匹配"""

    def __init__(self):
        self.use_simulated = True
        self.client = None
        self.collection_name = "ecommerce_knowledge"
        self._try_connect()
    
    def _try_connect(self):
        try:
            from pymilvus import MilvusClient, FieldSchema, CollectionSchema, DataType
            self.client = MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}")
            self.use_simulated = False
            self._init_collection()
        except Exception as e:
            print(f"Milvus连接失败，使用模拟数据: {e}", file=sys.stderr)
            self.use_simulated = True
    
    def _init_collection(self):
        if self.client is None:
            return
        try:
            if not self.client.has_collection(self.collection_name):
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=50, is_primary=True),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
                    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=500),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
                    FieldSchema(name="chunk_index", dtype=DataType.INT64),
                    FieldSchema(name="total_chunks", dtype=DataType.INT64)
                ]
                schema = CollectionSchema(fields=fields, description="E-commerce knowledge base")
                self.client.create_collection(collection_name=self.collection_name, schema=schema)
                self.client.create_index(
                    collection_name=self.collection_name,
                    field_name="vector",
                    index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 1024}}
                )
        except Exception as e:
            print(f"初始化集合失败: {e}", file=sys.stderr)
    
    def generate_vector(self, text: str) -> List[float]:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            return model.encode(text).tolist()
        except Exception as e:
            print(f"Vector generation error: {e}", file=sys.stderr)
            return [0.0] * VECTOR_DIM
    
    def _calculate_similarity(self, query: str, doc_content: str) -> float:
        query_words = set(query.lower().split())
        doc_words = set(doc_content.lower().split())
        if not query_words:
            return 0.0
        intersection = query_words & doc_words
        return len(intersection) / len(query_words)
    
    def search(self, query: str, top_k: int = 5, category_filter: str = None) -> List[Dict]:
        if self.use_simulated:
            results = []
            for i, doc in enumerate(SIMULATED_DATA):
                if category_filter and doc["category"] != category_filter:
                    continue
                score = self._calculate_similarity(query, doc["content"])
                if score > 0:
                    results.append({
                        "score": score,
                        "content": doc["content"],
                        "title": doc["title"],
                        "category": doc["category"],
                        "source": doc["source"],
                        "chunk_index": 0,
                        "total_chunks": 1
                    })
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        
        try:
            query_vector = self.generate_vector(query)
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            
            expr = None
            if category_filter:
                expr = f"category == '{category_filter}'"
            
            search_results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                limit=top_k,
                expr=expr,
                search_params=search_params,
                output_fields=["content", "title", "category", "source", "chunk_index", "total_chunks"]
            )
            
            ret = []
            for hit in search_results[0]:
                ret.append({
                    "score": hit["distance"],
                    "content": hit["entity"]["content"],
                    "title": hit["entity"]["title"],
                    "category": hit["entity"]["category"],
                    "source": hit["entity"]["source"],
                    "chunk_index": hit["entity"]["chunk_index"],
                    "total_chunks": hit["entity"]["total_chunks"]
                })
            return ret
        except Exception as e:
            print(f"搜索失败，使用模拟数据: {e}", file=sys.stderr)
            return self.search_simulated(query, top_k, category_filter)
    
    def search_simulated(self, query: str, top_k: int = 5, category_filter: str = None) -> List[Dict]:
        results = []
        for i, doc in enumerate(SIMULATED_DATA):
            if category_filter and doc["category"] != category_filter:
                continue
            score = self._calculate_similarity(query, doc["content"])
            if score > 0:
                results.append({
                    "score": score,
                    "content": doc["content"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "source": doc["source"],
                    "chunk_index": 0,
                    "total_chunks": 1
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def get_collection_stats(self) -> Dict:
        if self.use_simulated:
            return {
                "collection_name": self.collection_name,
                "status": "using_simulated_data",
                "document_count": len(SIMULATED_DATA),
                "description": "E-commerce knowledge base (simulated)"
            }
        
        try:
            return self.client.get_collection_stats(self.collection_name)
        except Exception as e:
            return {
                "error": str(e),
                "status": "simulated_mode",
                "document_count": len(SIMULATED_DATA)
            }

def validate_input(input_data: Dict) -> List[str]:
    missing = []
    if "action" not in input_data:
        missing.append("action")
    return missing

def retrieve_knowledge(query: str, top_k: int = 5, category: str = None) -> Dict:
    rag = ECommerceRAG()
    try:
        results = rag.search(query, top_k, category)
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "mode": "simulated" if rag.use_simulated else "real"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "mode": "simulated"
        }

def get_stats() -> Dict:
    rag = ECommerceRAG()
    try:
        stats = rag.get_collection_stats()
        return {
            "success": True,
            "stats": stats,
            "mode": "simulated" if rag.use_simulated else "real"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "mode": "simulated"
        }

def main():
    input_data = json.loads(sys.stdin.read())
    missing = validate_input(input_data)
    if missing:
        sys.stdout.buffer.write((json.dumps({"error": "输入不完整", "missing_fields": missing}, ensure_ascii=False) + "\n").encode('utf-8'))
        return
    
    action = input_data["action"]
    
    if action == "retrieve":
        query = input_data.get("query", "")
        top_k = input_data.get("top_k", 5)
        category = input_data.get("category", None)
        result = retrieve_knowledge(query, top_k, category)
    
    elif action == "stats":
        result = get_stats()
    
    else:
        result = {"error": "未知操作", "action": action}
    
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode('utf-8'))

if __name__ == "__main__":
    main()