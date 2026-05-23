"""Sample flow for Prefect on GKE validation (step 2.2)."""

import asyncio

import asyncpg
from prefect import flow, task

DB_USER = "workers-sa-dev@turbo-rag.iam"
DB_NAME = "rag_metadata"
DB_HOST = "127.0.0.1"
DB_PORT = 5432


@task
def hello() -> str:
    return "Hello from Prefect on GKE"


@task
async def check_cloudsql() -> str:
    conn = await asyncpg.connect(
        user=DB_USER,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
        ssl=None,
    )
    try:
        version = await conn.fetchval("SELECT version()")
        return f"Cloud SQL OK: {version[:40]}..."
    finally:
        await conn.close()


@flow(name="hello-flow", log_prints=True)
async def hello_flow() -> None:
    message = hello()
    print(message)
    db_status = await check_cloudsql()
    print(db_status)


if __name__ == "__main__":
    asyncio.run(hello_flow())
