"""Apply SQL migrations to rag_metadata."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


async def ensure_schema(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            revision TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    applied = {
        row["revision"]
        for row in await conn.fetch("SELECT revision FROM schema_migrations")
    }
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        revision = getattr(module, "revision", path.stem)
        if revision in applied:
            continue
        sql = getattr(module, "SQL", None)
        if not sql:
            continue
        logger.info("Applying migration %s", revision)
        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations (revision) VALUES ($1)", revision
            )
