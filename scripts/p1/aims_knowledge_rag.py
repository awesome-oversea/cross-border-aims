from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def dot_product(left: Sequence[float], right: Sequence[float]) -> float:
    return float(sum(a * b for a, b in zip(left, right)))


def batched(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for index in range(0, len(items), size):
        yield items[index:index + size]


@dataclass
class Record:
    record_id: str
    source_type: str
    source_id: str
    collection: str
    engine: str
    domain: str
    title: str
    text: str
    tags: List[str]
    source_path: str
    routing_score: int
    routing_reasons: List[str]
    metadata: Dict[str, Any]

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Record":
        return cls(
            record_id=str(payload["recordId"]),
            source_type=str(payload["sourceType"]),
            source_id=str(payload["sourceId"]),
            collection=str(payload["collection"]),
            engine=str(payload["engine"]),
            domain=str(payload["domain"]),
            title=str(payload.get("title", "")),
            text=str(payload.get("text", "")),
            tags=[str(item) for item in payload.get("tags", [])],
            source_path=str(payload.get("sourcePath", "")),
            routing_score=int(payload.get("routingScore", 0)),
            routing_reasons=[str(item) for item in payload.get("routingReasons", [])],
            metadata=dict(payload.get("metadata", {})),
        )

    def to_milvus_row(self, vector: List[float]) -> Dict[str, Any]:
        return {
            "id": self.record_id,
            "vector": vector,
            "title": self.title,
            "text": self.text,
            "collection": self.collection,
            "domain": self.domain,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "tags_json": json.dumps(self.tags, ensure_ascii=False),
            "routing_score": self.routing_score,
            "routing_reasons_json": json.dumps(self.routing_reasons, ensure_ascii=False),
            "metadata_json": json.dumps(self.metadata, ensure_ascii=False),
        }

    def to_qdrant_payload(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "title": self.title,
            "text": self.text,
            "collection": self.collection,
            "domain": self.domain,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "tags": self.tags,
            "routing_score": self.routing_score,
            "routing_reasons": self.routing_reasons,
            "metadata": self.metadata,
        }

    def qdrant_point_id(self) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"aims-record:{self.record_id}"))

    def embedding_text(self) -> str:
        parts: List[str] = []
        if self.title:
            # Weight concise titles a bit higher than long bodies.
            parts.extend([self.title, self.title])
        if self.tags:
            parts.append(" ".join(self.tags))
        if self.text:
            parts.append(self.text)
        return "\n".join(parts)


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def encode(self, texts: Sequence[str], batch_size: int) -> List[List[float]]:
        vectors = self._model.encode(
            list(texts),
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]


class HashBowEmbedder:
    _segment_pattern = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+")

    def __init__(self, dimension: int, model_name: str = "hash-bow") -> None:
        self.dimension = int(dimension)
        self.model_name = model_name

    @classmethod
    def _tokenize(cls, text: str) -> List[tuple[str, float]]:
        tokens: List[tuple[str, float]] = []
        for segment in cls._segment_pattern.findall(text):
            if re.fullmatch(r"[A-Za-z0-9_]+", segment):
                normalized = segment.lower()
                weight = 3.0 if any(character.isdigit() for character in normalized) else 1.5
                tokens.append((normalized, weight))
                continue

            tokens.append((segment, 1.25))
            tokens.extend((segment[index], 0.35) for index in range(len(segment)))
            if len(segment) >= 2:
                tokens.extend((segment[index:index + 2], 1.0) for index in range(len(segment) - 1))

        return tokens

    def _encode_one(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        tokens = self._tokenize(text)
        if not tokens:
            tokens = [("__empty__", 1.0)]

        for token, base_weight in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = base_weight * (1.0 + (digest[5] / 255.0))
            vector[index] += sign * weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def encode(self, texts: Sequence[str], batch_size: int) -> List[List[float]]:
        del batch_size
        return [self._encode_one(text) for text in texts]


def build_embedder(embedding_backend: str, model_name: str, vector_dimension: int):
    if embedding_backend == "hash-bow":
        return HashBowEmbedder(dimension=vector_dimension, model_name="hash-bow")
    if embedding_backend == "sentence-transformers":
        return SentenceTransformerEmbedder(model_name=model_name)
    raise ValueError(f"Unsupported embedding backend: {embedding_backend}")


class MilvusStore:
    def __init__(self, uri: str, dimension: int) -> None:
        from pymilvus import DataType, MilvusClient

        self._data_type = DataType
        self._client = MilvusClient(uri=uri)
        self._dimension = dimension

    def ensure_collection(self, collection_name: str, recreate_existing: bool) -> None:
        if self._client.has_collection(collection_name):
            if recreate_existing:
                self._client.drop_collection(collection_name=collection_name)
            else:
                self._client.load_collection(collection_name=collection_name)
                return

        schema = self._client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=self._data_type.VARCHAR, is_primary=True, max_length=200)
        schema.add_field(field_name="vector", datatype=self._data_type.FLOAT_VECTOR, dim=self._dimension)

        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="COSINE",
            index_name="vector_index",
        )

        self._client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params,
        )
        self._client.load_collection(collection_name=collection_name)

    def upsert(self, collection_name: str, rows: Sequence[Dict[str, Any]]) -> int:
        response = self._client.upsert(collection_name=collection_name, data=list(rows))
        return int(response.get("upsert_count", len(rows)))

    def search(self, collection_name: str, vector: List[float], limit: int) -> List[Dict[str, Any]]:
        response = self._client.search(
            collection_name=collection_name,
            data=[vector],
            limit=limit,
            anns_field="vector",
            output_fields=[
                "title",
                "text",
                "collection",
                "domain",
                "source_type",
                "source_id",
                "source_path",
                "tags_json",
                "metadata_json",
            ],
            search_params={"metric_type": "COSINE"},
        )

        hits = response[0] if response else []
        normalized: List[Dict[str, Any]] = []
        for hit in hits:
            entity = hit.get("entity", {})
            normalized.append(
                {
                    "id": hit.get("id"),
                    "score": hit.get("distance"),
                    "payload": entity,
                }
            )
        return normalized


class QdrantStore:
    def __init__(self, url: str, dimension: int) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client import models

        self._client = QdrantClient(url=url)
        self._models = models
        self._dimension = dimension

    def ensure_collection(self, collection_name: str, recreate_existing: bool) -> None:
        if self._client.collection_exists(collection_name):
            if recreate_existing:
                self._client.delete_collection(collection_name=collection_name)
            else:
                return

        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=self._models.VectorParams(
                size=self._dimension,
                distance=self._models.Distance.COSINE,
            ),
        )

    def upsert(self, collection_name: str, rows: Sequence[Record], vectors: Sequence[List[float]]) -> int:
        points = [
            self._models.PointStruct(
                id=record.qdrant_point_id(),
                vector=vector,
                payload=record.to_qdrant_payload(),
            )
            for record, vector in zip(rows, vectors)
        ]
        operation = self._client.upsert(collection_name=collection_name, points=points, wait=True)
        count = getattr(operation, "points_count", None)
        return int(count if count is not None else len(points))

    def search(self, collection_name: str, vector: List[float], limit: int) -> List[Dict[str, Any]]:
        response = self._client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        points = getattr(response, "points", response)
        normalized: List[Dict[str, Any]] = []
        for point in points:
            normalized.append(
                {
                    "id": getattr(point, "id", None),
                    "score": getattr(point, "score", None),
                    "payload": getattr(point, "payload", {}) or {},
                }
            )
        return normalized


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIMS knowledge RAG pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Embed and import knowledge records")
    import_parser.add_argument("--records-path", required=True)
    import_parser.add_argument("--plan-path", required=True)
    import_parser.add_argument("--report-path", required=True)
    import_parser.add_argument("--embedding-backend", choices=["hash-bow", "sentence-transformers"], default="hash-bow")
    import_parser.add_argument("--model-name", required=True)
    import_parser.add_argument("--vector-dimension", type=int, default=384)
    import_parser.add_argument("--milvus-uri", default="http://127.0.0.1:19530")
    import_parser.add_argument("--qdrant-url", default="http://127.0.0.1:6333")
    import_parser.add_argument("--batch-size", type=int, default=32)
    import_parser.add_argument("--recreate-existing", action="store_true")
    import_parser.add_argument("--dry-run", action="store_true")

    check_parser = subparsers.add_parser("check", help="Run retrieval checks against imported collections")
    check_parser.add_argument("--query-case-path", required=True)
    check_parser.add_argument("--records-path")
    check_parser.add_argument("--report-path", required=True)
    check_parser.add_argument("--embedding-backend", choices=["hash-bow", "sentence-transformers"], default="hash-bow")
    check_parser.add_argument("--model-name", required=True)
    check_parser.add_argument("--vector-dimension", type=int, default=384)
    check_parser.add_argument("--milvus-uri", default="http://127.0.0.1:19530")
    check_parser.add_argument("--qdrant-url", default="http://127.0.0.1:6333")
    check_parser.add_argument("--top-k", type=int, default=5)
    check_parser.add_argument("--offline", action="store_true")

    return parser


def load_records(path: Path) -> List[Record]:
    return [Record.from_dict(item) for item in load_jsonl(path)]


def import_records(args: argparse.Namespace) -> int:
    records = load_records(Path(args.records_path))
    plan = load_json(Path(args.plan_path))
    embedder = build_embedder(args.embedding_backend, args.model_name, args.vector_dimension)
    dimension = embedder.dimension

    plan_by_collection = {item["collection"]: item for item in plan}
    grouped_records: Dict[str, List[Record]] = {}
    for record in records:
        grouped_records.setdefault(record.collection, []).append(record)

    milvus_store = None
    qdrant_store = None
    if not args.dry_run:
        if any(record.engine == "milvus" for record in records):
            milvus_store = MilvusStore(uri=args.milvus_uri, dimension=dimension)
        if any(record.engine == "qdrant" for record in records):
            qdrant_store = QdrantStore(url=args.qdrant_url, dimension=dimension)

    report_collections: List[Dict[str, Any]] = []
    total_imported = 0

    for collection_name, collection_records in sorted(grouped_records.items(), key=lambda item: plan_by_collection[item[0]]["importOrder"]):
        engine = collection_records[0].engine
        plan_entry = plan_by_collection[collection_name]
        texts = [record.embedding_text() for record in collection_records]
        vectors = embedder.encode(texts, batch_size=args.batch_size)

        collection_report: Dict[str, Any] = {
            "collection": collection_name,
            "engine": engine,
            "domain": collection_records[0].domain,
            "recordCount": len(collection_records),
            "embeddingModel": args.model_name,
            "vectorDimension": dimension,
            "importOrder": plan_entry["importOrder"],
            "dryRun": bool(args.dry_run),
        }

        if args.dry_run:
            collection_report["importedCount"] = len(collection_records)
            collection_report["status"] = "DRY_RUN"
            collection_report["sampleVectorPreview"] = vectors[0][:8] if vectors else []
            total_imported += len(collection_records)
            report_collections.append(collection_report)
            continue

        if engine == "milvus":
            assert milvus_store is not None
            milvus_store.ensure_collection(collection_name=collection_name, recreate_existing=args.recreate_existing)
            imported_count = 0
            for batch_records, batch_vectors in zip(batched(collection_records, args.batch_size), batched(vectors, args.batch_size)):
                rows = [record.to_milvus_row(vector) for record, vector in zip(batch_records, batch_vectors)]
                imported_count += milvus_store.upsert(collection_name=collection_name, rows=rows)
        else:
            assert qdrant_store is not None
            qdrant_store.ensure_collection(collection_name=collection_name, recreate_existing=args.recreate_existing)
            imported_count = 0
            for batch_records, batch_vectors in zip(batched(collection_records, args.batch_size), batched(vectors, args.batch_size)):
                imported_count += qdrant_store.upsert(collection_name=collection_name, rows=batch_records, vectors=batch_vectors)

        total_imported += imported_count
        collection_report["importedCount"] = imported_count
        collection_report["status"] = "IMPORTED"
        report_collections.append(collection_report)

    report = {
        "generatedAt": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "recordsPath": str(Path(args.records_path)),
        "planPath": str(Path(args.plan_path)),
        "embeddingBackend": args.embedding_backend,
        "embeddingModel": args.model_name,
        "vectorDimension": dimension,
        "batchSize": args.batch_size,
        "dryRun": bool(args.dry_run),
        "recreateExisting": bool(args.recreate_existing),
        "collections": report_collections,
        "totalImported": total_imported,
    }
    dump_json(Path(args.report_path), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def evaluate_case(case: Dict[str, Any], hits: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    expected_keywords = [str(item) for item in case.get("expectedKeywords", [])]
    top_hit = hits[0] if hits else None
    matched_keywords: List[str] = []
    if top_hit is not None:
        searchable = json.dumps(top_hit.get("payload", {}), ensure_ascii=False).lower()
        searchable += " " + str(top_hit.get("id", "")).lower()
        for keyword in expected_keywords:
            if keyword.lower() in searchable:
                matched_keywords.append(keyword)

    passed = bool(top_hit) and (len(expected_keywords) == 0 or len(matched_keywords) > 0)
    return {
        "id": case["id"],
        "collection": case["collection"],
        "query": case["query"],
        "expectedKeywords": expected_keywords,
        "matchedKeywords": matched_keywords,
        "passed": passed,
        "topHit": top_hit,
        "hitCount": len(hits),
    }


def run_checks(args: argparse.Namespace) -> int:
    cases = load_json(Path(args.query_case_path)).get("cases", [])
    embedder = build_embedder(args.embedding_backend, args.model_name, args.vector_dimension)
    dimension = embedder.dimension
    offline_index: Dict[str, List[Dict[str, Any]]] = {}
    milvus_store = None
    qdrant_store = None

    if args.offline:
        if not args.records_path:
            raise ValueError("--records-path is required when --offline is used.")

        records = load_records(Path(args.records_path))
        grouped_records: Dict[str, List[Record]] = {}
        for record in records:
            grouped_records.setdefault(record.collection, []).append(record)

        for collection_name, collection_records in grouped_records.items():
            vectors = embedder.encode([record.embedding_text() for record in collection_records], batch_size=64)
            offline_index[collection_name] = [
                {
                    "record": record,
                    "vector": vector,
                }
                for record, vector in zip(collection_records, vectors)
            ]
    else:
        milvus_store = MilvusStore(uri=args.milvus_uri, dimension=dimension)
        qdrant_store = QdrantStore(url=args.qdrant_url, dimension=dimension)

    results: List[Dict[str, Any]] = []
    failures: List[str] = []

    for case in cases:
        collection_name = case["collection"]
        query_vector = embedder.encode([case["query"]], batch_size=1)[0]
        if args.offline:
            candidates = offline_index.get(collection_name, [])
            ranked = sorted(
                candidates,
                key=lambda item: dot_product(query_vector, item["vector"]),
                reverse=True,
            )[: args.top_k]
            hits = [
                {
                    "id": item["record"].record_id,
                    "score": dot_product(query_vector, item["vector"]),
                    "payload": item["record"].to_qdrant_payload(),
                }
                for item in ranked
            ]
        elif collection_name in {"ecom_rules", "products", "after_sales"}:
            assert milvus_store is not None
            hits = milvus_store.search(collection_name=collection_name, vector=query_vector, limit=args.top_k)
        else:
            assert qdrant_store is not None
            hits = qdrant_store.search(collection_name=collection_name, vector=query_vector, limit=args.top_k)

        result = evaluate_case(case=case, hits=hits)
        results.append(result)
        if not result["passed"]:
            failures.append(case["id"])

    report = {
        "generatedAt": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "queryCasePath": str(Path(args.query_case_path)),
        "recordsPath": str(Path(args.records_path)) if args.records_path else None,
        "embeddingBackend": args.embedding_backend,
        "embeddingModel": args.model_name,
        "vectorDimension": dimension,
        "topK": args.top_k,
        "offline": bool(args.offline),
        "results": results,
        "passedCount": sum(1 for item in results if item["passed"]),
        "failedCount": len(failures),
        "failedIds": failures,
    }
    dump_json(Path(args.report_path), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failures else 0


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.command == "import":
        return import_records(args)
    if args.command == "check":
        return run_checks(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ModuleNotFoundError as exc:
        missing_module = exc.name or "unknown"
        print(
            "Missing Python dependency: "
            f"{missing_module}. Run `powershell -File scripts/p1/Install-AimsRagDependencies.ps1` first. "
            "If you want semantic local embeddings, add `-IncludeSentenceTransformers`.",
            file=sys.stderr,
        )
        raise SystemExit(2)
