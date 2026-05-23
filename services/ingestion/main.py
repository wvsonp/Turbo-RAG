import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from rag_platform.config import DispatcherConfig
from rag_platform.logging_utils import configure_logging

from dispatcher import Dispatcher

SERVICE_NAME = os.getenv("SERVICE_NAME", "ingestion")
logger = configure_logging(SERVICE_NAME)

_dispatcher: Dispatcher | None = None
_dispatcher_thread: threading.Thread | None = None


def _start_dispatcher() -> None:
    global _dispatcher, _dispatcher_thread
    if os.getenv("DISPATCHER_ENABLED", "true").lower() != "true":
        logger.info("Dispatcher disabled via DISPATCHER_ENABLED")
        return
    config = DispatcherConfig.from_env()
    _dispatcher = Dispatcher(config)
    _dispatcher_thread = threading.Thread(
        target=_dispatcher.run_forever, name="pubsub-dispatcher", daemon=True
    )
    _dispatcher_thread.start()
    logger.info("Dispatcher thread started")


def _stop_dispatcher() -> None:
    global _dispatcher
    if _dispatcher:
        _dispatcher.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _start_dispatcher()
    yield
    _stop_dispatcher()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if os.getenv("DISPATCHER_ENABLED", "true").lower() == "true":
        if _dispatcher_thread is None or not _dispatcher_thread.is_alive():
            return PlainTextResponse("dispatcher not running", status_code=503)
    return {"status": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return "# HELP up Service up\n# TYPE up gauge\nup 1\n"
