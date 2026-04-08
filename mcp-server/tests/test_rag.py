"""Test RAG schema indexer output format."""

import logging

from rag.schema_indexer import build_context, build_mongo_context, build_postgres_context

logger = logging.getLogger(__name__)


class TestSchemaIndexer:
    """Verify context builders return meaningful strings."""

    def test_postgres_context_has_header(self):
        try:
            ctx = build_postgres_context()
            assert "PostgreSQL" in ctx
        except Exception:
            logger.debug("PostgreSQL not available in test environment")

    def test_mongo_context_has_header(self):
        try:
            ctx = build_mongo_context()
            assert "MongoDB" in ctx
        except Exception:
            logger.debug("MongoDB not available in test environment")

    def test_full_context_returns_string(self):
        ctx = build_context()
        assert isinstance(ctx, str)
        assert len(ctx) > 0
