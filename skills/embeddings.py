# -*- coding: utf-8 -*-
"""Shared embedding utility using Ollama. Falls back to deterministic hash-based vectors."""
import json
import hashlib
import random
import os
import urllib.request
from typing import List, Optional

# Ollama本地Embedding服务配置，不可用时降级为基于哈希的确定性伪随机向量
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
VECTOR_DIM = 768


def _ollama_embed(text: str) -> Optional[List[float]]:
    """Get embedding from Ollama. Returns None if unavailable."""
    try:
        data = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/embeddings", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("embedding")
    except Exception:
        return None


def _pseudo_embedding(text: str, dim: int = VECTOR_DIM) -> List[float]:
    """Deterministic fallback: seeded random based on text hash."""
    h = hashlib.sha256(text.encode('utf-8')).digest()
    rng = random.Random(h)
    vec = [rng.random() for _ in range(dim)]
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm for x in vec]


def embed(text: str, dim: int = VECTOR_DIM) -> List[float]:
    """Get embedding: Ollama first, fallback to pseudo."""
    vec = _ollama_embed(text)
    if vec and len(vec) == dim:
        return vec
    return _pseudo_embedding(text, dim)


def embed_many(texts: List[str], dim: int = VECTOR_DIM) -> List[List[float]]:
    """Embed multiple texts."""
    return [embed(t, dim) for t in texts]
