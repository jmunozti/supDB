import json

import psycopg2
import psycopg2.extras

from config import settings


def _connect():
    return psycopg2.connect(settings.postgres_dsn)


def get_slow_queries(limit: int = 10) -> str:
    """Get the slowest queries from pg_stat_statements."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    queryid,
                    LEFT(query, 200) AS query,
                    calls,
                    ROUND(total_exec_time::numeric, 2) AS total_time_ms,
                    ROUND(mean_exec_time::numeric, 2) AS avg_time_ms,
                    ROUND(max_exec_time::numeric, 2) AS max_time_ms,
                    rows
                FROM pg_stat_statements
                WHERE userid = (SELECT usesysid FROM pg_user WHERE usename = current_user)
                ORDER BY mean_exec_time DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
    return json.dumps(rows, default=str)


def explain_query(query: str) -> str:
    """Run EXPLAIN ANALYZE on a query and return the execution plan."""
    # Safety: only allow SELECT queries
    stripped = query.strip().upper()
    if not stripped.startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed for EXPLAIN."})

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}")
            plan = cur.fetchone()[0]
            conn.rollback()  # Don't commit anything
    return json.dumps(plan, default=str, indent=2)


def get_missing_indexes() -> str:
    """Find tables with sequential scans that could benefit from indexes."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    schemaname,
                    relname AS table_name,
                    seq_scan,
                    seq_tup_read,
                    idx_scan,
                    idx_tup_fetch,
                    n_tup_ins + n_tup_upd + n_tup_del AS writes,
                    pg_size_pretty(pg_relation_size(relid)) AS table_size
                FROM pg_stat_user_tables
                WHERE seq_scan > 0
                ORDER BY seq_tup_read DESC
                LIMIT 20
            """)
            rows = cur.fetchall()
    return json.dumps(rows, default=str)


def get_table_indexes(table_name: str) -> str:
    """List all indexes on a specific table."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    indexname,
                    indexdef,
                    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
                FROM pg_indexes
                WHERE tablename = %s AND schemaname = 'public'
            """, (table_name,))
            rows = cur.fetchall()
    return json.dumps(rows, default=str)


def get_table_stats(table_name: str) -> str:
    """Get detailed statistics for a specific table."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    relname AS table_name,
                    n_live_tup AS live_rows,
                    n_dead_tup AS dead_rows,
                    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_row_pct,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    seq_scan,
                    idx_scan,
                    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
                FROM pg_stat_user_tables
                WHERE relname = %s
            """, (table_name,))
            row = cur.fetchone()
    return json.dumps(row, default=str)


def get_schema() -> str:
    """Get the full database schema: tables, columns, types, and constraints."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    t.table_name,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    tc.constraint_type
                FROM information_schema.tables t
                JOIN information_schema.columns c
                    ON t.table_name = c.table_name AND t.table_schema = c.table_schema
                LEFT JOIN information_schema.key_column_usage kcu
                    ON c.table_name = kcu.table_name AND c.column_name = kcu.column_name
                LEFT JOIN information_schema.table_constraints tc
                    ON kcu.constraint_name = tc.constraint_name
                WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name, c.ordinal_position
            """)
            rows = cur.fetchall()
    return json.dumps(rows, default=str)


def get_active_connections() -> str:
    """Show current active connections and their state."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    pid,
                    usename,
                    state,
                    LEFT(query, 150) AS query,
                    query_start,
                    NOW() - query_start AS duration,
                    wait_event_type,
                    wait_event
                FROM pg_stat_activity
                WHERE datname = current_database() AND pid != pg_backend_pid()
                ORDER BY query_start ASC
            """)
            rows = cur.fetchall()
    return json.dumps(rows, default=str)
