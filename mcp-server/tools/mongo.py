import json
from datetime import datetime

from pymongo import MongoClient

from config import settings


def _connect():
    client = MongoClient(settings.mongo_uri)
    return client[settings.mongo_db]


def _serialize(obj):
    """Handle MongoDB types for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__str__"):
        return str(obj)
    return obj


def get_slow_queries(limit: int = 10) -> str:
    """Get slow operations from MongoDB profiler."""
    db = _connect()
    profiler_data = list(
        db.system.profile.find(
            {"millis": {"$gt": 0}},
            {
                "op": 1,
                "ns": 1,
                "millis": 1,
                "command": 1,
                "planSummary": 1,
                "docsExamined": 1,
                "nreturned": 1,
                "ts": 1,
            },
        )
        .sort("millis", -1)
        .limit(limit)
    )

    results = []
    for doc in profiler_data:
        results.append({
            "operation": doc.get("op"),
            "namespace": doc.get("ns"),
            "duration_ms": doc.get("millis"),
            "plan": doc.get("planSummary"),
            "docs_examined": doc.get("docsExamined"),
            "docs_returned": doc.get("nreturned"),
            "timestamp": doc.get("ts"),
            "command": str(doc.get("command", ""))[:200],
        })
    return json.dumps(results, default=_serialize)


def get_collection_stats(collection_name: str) -> str:
    """Get detailed stats for a MongoDB collection."""
    db = _connect()
    stats = db.command("collStats", collection_name)

    return json.dumps({
        "namespace": stats.get("ns"),
        "document_count": stats.get("count"),
        "avg_doc_size_bytes": stats.get("avgObjSize"),
        "total_size_mb": round(stats.get("totalSize", 0) / 1024 / 1024, 2),
        "storage_size_mb": round(stats.get("storageSize", 0) / 1024 / 1024, 2),
        "index_count": stats.get("nindexes"),
        "total_index_size_mb": round(stats.get("totalIndexSize", 0) / 1024 / 1024, 2),
    }, default=_serialize)


def get_collection_indexes(collection_name: str) -> str:
    """List all indexes on a MongoDB collection."""
    db = _connect()
    indexes = list(db[collection_name].list_indexes())

    results = []
    for idx in indexes:
        results.append({
            "name": idx.get("name"),
            "keys": {k: v for k, v in idx.get("key", {}).items()},
            "unique": idx.get("unique", False),
            "sparse": idx.get("sparse", False),
        })
    return json.dumps(results, default=_serialize)


def find_missing_indexes() -> str:
    """Analyze profiler data to find queries doing collection scans (COLLSCAN)."""
    db = _connect()
    collscans = list(
        db.system.profile.find(
            {"planSummary": "COLLSCAN"},
            {"ns": 1, "millis": 1, "command": 1, "planSummary": 1, "docsExamined": 1},
        )
        .sort("millis", -1)
        .limit(20)
    )

    results = []
    for doc in collscans:
        cmd = doc.get("command", {})
        filter_keys = list(cmd.get("filter", {}).keys()) if isinstance(cmd, dict) else []
        sort_keys = list(cmd.get("sort", {}).keys()) if isinstance(cmd, dict) else []

        results.append({
            "namespace": doc.get("ns"),
            "duration_ms": doc.get("millis"),
            "docs_examined": doc.get("docsExamined"),
            "filter_fields": filter_keys,
            "sort_fields": sort_keys,
            "suggested_index": filter_keys + sort_keys,
        })
    return json.dumps(results, default=_serialize)


def get_all_collections() -> str:
    """List all collections with document counts and sizes."""
    db = _connect()
    collections = db.list_collection_names()

    results = []
    for name in collections:
        if name == "system.profile":
            continue
        stats = db.command("collStats", name)
        results.append({
            "name": name,
            "document_count": stats.get("count"),
            "avg_doc_size_bytes": stats.get("avgObjSize"),
            "total_size_mb": round(stats.get("totalSize", 0) / 1024 / 1024, 2),
            "index_count": stats.get("nindexes"),
        })
    return json.dumps(results, default=_serialize)


def get_schema_sample(collection_name: str) -> str:
    """Get a sample document to infer the schema of a collection."""
    db = _connect()
    sample = db[collection_name].find_one({}, {"_id": 0})
    if not sample:
        return json.dumps({"error": f"Collection '{collection_name}' is empty."})

    def infer_type(value):
        if isinstance(value, dict):
            return {k: infer_type(v) for k, v in value.items()}
        if isinstance(value, list):
            return [infer_type(value[0])] if value else ["empty"]
        return type(value).__name__

    schema = {k: infer_type(v) for k, v in sample.items()}
    return json.dumps({"collection": collection_name, "schema": schema, "sample": sample}, default=_serialize)
