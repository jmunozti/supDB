"""Indexes database schemas, stats, and metadata into a context string.

This is NOT a vector DB RAG — it builds a live text snapshot of both databases
so Claude has full context when answering questions about performance.
Every time a user asks something, the MCP server calls build_context()
to give Claude an up-to-date picture of the database state.
"""

import json
import logging

from tools.mongo import find_missing_indexes as mongo_missing_indexes
from tools.mongo import get_all_collections, get_schema_sample
from tools.postgres import get_missing_indexes as pg_missing_indexes
from tools.postgres import get_schema

logger = logging.getLogger(__name__)


def build_postgres_context() -> str:
    """Build a text summary of the PostgreSQL database state."""
    schema = json.loads(get_schema())
    missing = json.loads(pg_missing_indexes())

    lines = ["## PostgreSQL Database Context\n"]

    # Group schema by table
    tables: dict[str, list] = {}
    for col in schema:
        table = col["table_name"]
        tables.setdefault(table, []).append(col)

    for table, columns in tables.items():
        lines.append(f"### Table: {table}")
        for col in columns:
            constraint = f" [{col['constraint_type']}]" if col.get("constraint_type") else ""
            nullable = " NULL" if col["is_nullable"] == "YES" else " NOT NULL"
            lines.append(f"  - {col['column_name']}: {col['data_type']}{nullable}{constraint}")
        lines.append("")

    # Missing indexes
    if missing:
        lines.append("### Tables needing indexes (high seq scans):")
        for t in missing[:10]:
            ratio = t["seq_scan"] / max(t.get("idx_scan") or 1, 1)
            lines.append(
                f"  - {t['table_name']}: {t['seq_scan']} seq scans "
                f"vs {t.get('idx_scan', 0)} idx scans "
                f"(ratio: {ratio:.1f}x), size: {t['table_size']}"
            )
        lines.append("")

    return "\n".join(lines)


def build_mongo_context() -> str:
    """Build a text summary of the MongoDB database state."""
    collections = json.loads(get_all_collections())
    missing = json.loads(mongo_missing_indexes())

    lines = ["## MongoDB Database Context\n"]

    for col in collections:
        lines.append(f"### Collection: {col['name']}")
        lines.append(f"  - Documents: {col['document_count']}")
        lines.append(f"  - Avg doc size: {col['avg_doc_size_bytes']} bytes")
        lines.append(f"  - Total size: {col['total_size_mb']} MB")
        lines.append(f"  - Indexes: {col['index_count']}")

        try:
            sample = json.loads(get_schema_sample(col["name"]))
            if "schema" in sample:
                lines.append(f"  - Schema: {json.dumps(sample['schema'])}")
        except Exception:
            logger.debug("Could not get schema sample for %s", col["name"])
        lines.append("")

    # Collection scans
    if missing:
        lines.append("### Queries doing full collection scans (COLLSCAN):")
        for m in missing[:10]:
            lines.append(
                f"  - {m['namespace']}: {m['duration_ms']}ms, "
                f"examined {m['docs_examined']} docs"
            )
            if m.get("suggested_index"):
                lines.append(f"    Suggested index on: {m['suggested_index']}")
        lines.append("")

    return "\n".join(lines)


def build_context() -> str:
    """Build the complete RAG context from both databases."""
    parts = []

    try:
        parts.append(build_postgres_context())
    except Exception as e:
        parts.append(f"## PostgreSQL: unavailable ({e})\n")

    try:
        parts.append(build_mongo_context())
    except Exception as e:
        parts.append(f"## MongoDB: unavailable ({e})\n")

    return "\n".join(parts)
