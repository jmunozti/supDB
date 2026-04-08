"""Test that the MCP server only allows safe operations."""

import json

from tools.postgres import explain_query


class TestPostgresSafety:
    """Ensure only SELECT queries are allowed in EXPLAIN."""

    def test_rejects_delete(self):
        result = json.loads(explain_query("DELETE FROM customers"))
        assert "error" in result

    def test_rejects_drop(self):
        result = json.loads(explain_query("DROP TABLE customers"))
        assert "error" in result

    def test_rejects_update(self):
        result = json.loads(explain_query("UPDATE customers SET name = 'x'"))
        assert "error" in result

    def test_rejects_insert(self):
        result = json.loads(explain_query("INSERT INTO customers (name) VALUES ('x')"))
        assert "error" in result

    def test_rejects_truncate(self):
        result = json.loads(explain_query("TRUNCATE customers"))
        assert "error" in result
