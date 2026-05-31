import os
import logging
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

SERVICE_NAME = os.getenv("SERVICE_NAME", "unknown")

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","service":"' + SERVICE_NAME + '","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"status": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return "# HELP up Service up\n# TYPE up gauge\nup 1\n"


@app.on_event("startup")
async def startup():
    logger.info("started")
