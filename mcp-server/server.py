"""
supDB — "Sup, DB?"

An MCP server for Claude Code that connects to PostgreSQL and MongoDB,
finds slow queries, suggests indexes, and provides database context.
"""

from mcp.server.fastmcp import FastMCP

from rag.schema_indexer import build_context
from tools import mongo, postgres

mcp = FastMCP(
    "supdb",
    instructions="""You are a database performance expert. You have access to PostgreSQL and MongoDB
databases. Use the available tools to diagnose slow queries, find missing indexes,
and suggest performance improvements. Always start by getting the database context
to understand the current state before making recommendations.""",
)


# ==================== Resource: Database Context ====================

@mcp.resource("db://context")
def database_context() -> str:
    """Live snapshot of both database schemas, stats, and potential issues."""
    return build_context()


# ==================== PostgreSQL Tools ====================

@mcp.tool()
def pg_slow_queries(limit: int = 10) -> str:
    """Find the slowest PostgreSQL queries by average execution time.

    Uses pg_stat_statements to identify queries that need optimization.
    Returns: query text, call count, avg/max time, and rows affected.
    """
    return postgres.get_slow_queries(limit)


@mcp.tool()
def pg_explain(query: str) -> str:
    """Run EXPLAIN ANALYZE on a SELECT query to see its execution plan.

    Shows how PostgreSQL executes the query: seq scans, index scans,
    join methods, buffer usage, and actual vs estimated rows.
    Only SELECT queries are allowed for safety.
    """
    return postgres.explain_query(query)


@mcp.tool()
def pg_missing_indexes() -> str:
    """Find PostgreSQL tables with high sequential scan counts.

    Tables with many seq scans relative to index scans likely need indexes.
    Shows scan counts, row reads, write volume, and table size.
    """
    return postgres.get_missing_indexes()


@mcp.tool()
def pg_table_indexes(table_name: str) -> str:
    """List all indexes on a PostgreSQL table.

    Shows index name, definition (columns and type), and size.
    Use this to check what indexes already exist before suggesting new ones.
    """
    return postgres.get_table_indexes(table_name)


@mcp.tool()
def pg_table_stats(table_name: str) -> str:
    """Get detailed statistics for a PostgreSQL table.

    Shows live/dead rows, dead row percentage, vacuum history,
    scan counts, and total size. Useful for identifying bloat and maintenance issues.
    """
    return postgres.get_table_stats(table_name)


@mcp.tool()
def pg_schema() -> str:
    """Get the complete PostgreSQL database schema.

    Lists all tables, columns, data types, nullability, defaults, and constraints.
    Use this to understand the database structure.
    """
    return postgres.get_schema()


@mcp.tool()
def pg_active_connections() -> str:
    """Show active PostgreSQL connections and what they're doing.

    Lists PIDs, users, states, current queries, duration, and wait events.
    Useful for finding long-running queries or connection leaks.
    """
    return postgres.get_active_connections()


# ==================== MongoDB Tools ====================

@mcp.tool()
def mongo_slow_queries(limit: int = 10) -> str:
    """Find the slowest MongoDB operations from the profiler.

    Shows operation type, namespace, duration, execution plan,
    documents examined vs returned. Helps identify inefficient queries.
    """
    return mongo.get_slow_queries(limit)


@mcp.tool()
def mongo_collection_stats(collection_name: str) -> str:
    """Get detailed stats for a MongoDB collection.

    Shows document count, average doc size, total/storage size,
    index count, and index size.
    """
    return mongo.get_collection_stats(collection_name)


@mcp.tool()
def mongo_collection_indexes(collection_name: str) -> str:
    """List all indexes on a MongoDB collection.

    Shows index name, key fields and directions, and properties (unique, sparse).
    Use to check existing indexes before suggesting new ones.
    """
    return mongo.get_collection_indexes(collection_name)


@mcp.tool()
def mongo_missing_indexes() -> str:
    """Find MongoDB queries doing full collection scans (COLLSCAN).

    Analyzes the profiler to find queries without proper indexes.
    Suggests which fields should be indexed based on filter and sort patterns.
    """
    return mongo.find_missing_indexes()


@mcp.tool()
def mongo_collections() -> str:
    """List all MongoDB collections with document counts and sizes."""
    return mongo.get_all_collections()


@mcp.tool()
def mongo_schema(collection_name: str) -> str:
    """Infer the schema of a MongoDB collection from a sample document.

    Shows field names, inferred types, and a sample document.
    Useful for understanding document structure.
    """
    return mongo.get_schema_sample(collection_name)


# ==================== Entry Point ====================

if __name__ == "__main__":
    mcp.run()
