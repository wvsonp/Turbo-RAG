"""Pub/Sub dispatcher: pull messages, start Prefect runs, ack on success."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from google.cloud import pubsub_v1

from rag_platform.config import DispatcherConfig
from rag_platform.contracts import document_version_id

logger = logging.getLogger(__name__)

TERMINAL_STATES = {"COMPLETED", "FAILED", "CRASHED", "CANCELLED"}
SUCCESS_STATES = {"COMPLETED"}


@dataclass
class PulledMessage:
    ack_id: str
    message_id: str
    data: bytes


@dataclass
class InFlightRun:
    ack_id: str
    pubsub_message_id: str
    document_version_id: str
    prefect_flow_run_id: str
    started_at: float = field(default_factory=time.monotonic)


class PrefectClient:
    def __init__(self, config: DispatcherConfig) -> None:
        self._config = config
        self._deployment_id: str | None = None

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._config.prefect_api_url,
            timeout=30.0,
        )

    async def resolve_deployment_id(self) -> str:
        if self._deployment_id:
            return self._deployment_id
        flow_name, _, deploy_name = self._config.prefect_deployment_name.partition(
            "/"
        )
        if not deploy_name:
            deploy_name = flow_name
            flow_name = "ingest-document"
        async with await self._client() as client:
            resp = await client.post(
                "/deployments/filter",
                json={
                    "deployments": {
                        "operator": "and_",
                        "name": {"any_": [deploy_name]},
                    },
                    "flows": {
                        "operator": "and_",
                        "name": {"any_": [flow_name]},
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                raise RuntimeError(
                    "Prefect deployment not found: "
                    f"{self._config.prefect_deployment_name}"
                )
            self._deployment_id = data[0]["id"]
            return self._deployment_id

    async def create_flow_run(self, parameters: dict[str, Any]) -> str:
        deployment_id = await self._resolve_deployment_id()
        async with await self._client() as client:
            resp = await client.post(
                f"/deployments/{deployment_id}/create_flow_run",
                json={"parameters": parameters},
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def _resolve_deployment_id(self) -> str:
        return await self.resolve_deployment_id()

    async def get_flow_run_state(self, flow_run_id: str) -> str:
        async with await self._client() as client:
            resp = await client.get(f"/flow_runs/{flow_run_id}")
            resp.raise_for_status()
            state = resp.json().get("state", {})
            return state.get("type", "PENDING")

    async def find_running_flow_run(self, version_key: str) -> str | None:
        async with await self._client() as client:
            resp = await client.post(
                "/flow_runs/filter",
                json={
                    "flow_runs": {
                        "operator": "and_",
                        "state": {
                            "operator": "and_",
                            "type": {
                                "any_": ["RUNNING", "PENDING", "SCHEDULED"]
                            },
                        },
                    },
                    "sort": "START_TIME_DESC",
                    "limit": 20,
                },
            )
            resp.raise_for_status()
            for run in resp.json():
                params = run.get("parameters") or {}
                bucket = params.get("bucket", "")
                obj = params.get("object_name", "")
                gen = params.get("generation", "")
                if document_version_id(bucket, obj, gen) == version_key:
                    return run["id"]
        return None


class Dispatcher:
    def __init__(self, config: DispatcherConfig) -> None:
        self._config = config
        self._subscriber = pubsub_v1.SubscriberClient()
        self._subscription_path = self._subscriber.subscription_path(
            config.project_id, config.subscription
        )
        self._dlq_subscription_path = (
            self._subscriber.subscription_path(
                config.project_id, config.dlq_subscription
            )
            if config.dlq_subscription
            else None
        )
        self._prefect = PrefectClient(config)
        self._in_flight: dict[str, InFlightRun] = {}
        self._lock = threading.Lock()
        self._metrics_lock = threading.Lock()
        self._stop = threading.Event()
        self._ingestion_runs_total = 0
        self._ingestion_failures_total = 0
        self._dlq_undelivered_messages = 0
        self._last_dlq_poll = time.monotonic()

    def stop(self) -> None:
        self._stop.set()

    def metrics_text(self) -> str:
        with self._metrics_lock:
            runs = self._ingestion_runs_total
            failures = self._ingestion_failures_total
            dlq_depth = self._dlq_undelivered_messages
        lines = [
            "# HELP up Service up",
            "# TYPE up gauge",
            "up 1",
            "# HELP ingestion_runs_total Prefect ingestion runs started by dispatcher",
            "# TYPE ingestion_runs_total counter",
            f"ingestion_runs_total {runs}",
            "# HELP ingestion_failures_total Ingestion runs nacked due to failure or timeout",
            "# TYPE ingestion_failures_total counter",
            f"ingestion_failures_total {failures}",
            "# HELP dlq_undelivered_messages Approximate DLQ subscription depth (0 or more)",
            "# TYPE dlq_undelivered_messages gauge",
            f"dlq_undelivered_messages {dlq_depth}",
        ]
        return "\n".join(lines) + "\n"

    def _record_run_started(self) -> None:
        with self._metrics_lock:
            self._ingestion_runs_total += 1

    def _record_failure(
        self,
        *,
        reason: str,
        document_version_id: str,
        pubsub_message_id: str,
        prefect_flow_run_id: str | None = None,
    ) -> None:
        with self._metrics_lock:
            self._ingestion_failures_total += 1
        logger.warning(
            "Ingestion nack reason=%s document_version_id=%s pubsub_message_id=%s prefect_flow_run_id=%s",
            reason,
            document_version_id,
            pubsub_message_id,
            prefect_flow_run_id or "",
        )

    def run_forever(self) -> None:
        logger.info(
            "Dispatcher starting subscription=%s dlq_subscription=%s max_concurrent=%d",
            self._config.subscription,
            self._config.dlq_subscription or "(disabled)",
            self._config.max_concurrent_runs,
        )
        asyncio.run(self._run_loop())

    async def _run_loop(self) -> None:
        await self._prefect.resolve_deployment_id()
        while not self._stop.is_set():
            await self._poll_dlq_depth_if_due()
            await self._poll_in_flight()
            capacity = self._config.max_concurrent_runs - len(self._in_flight)
            if capacity <= 0:
                await asyncio.sleep(self._config.poll_interval_seconds)
                continue
            messages = await asyncio.to_thread(
                self._pull_messages, min(capacity, 10)
            )
            for pulled in messages:
                await self._handle_message(pulled)
            await asyncio.sleep(self._config.poll_interval_seconds)

    async def _poll_dlq_depth_if_due(self) -> None:
        if not self._dlq_subscription_path:
            return
        now = time.monotonic()
        if now - self._last_dlq_poll < self._config.dlq_poll_interval_seconds:
            return
        self._last_dlq_poll = now
        await asyncio.to_thread(self._sample_dlq_depth)

    def _sample_dlq_depth(self) -> None:
        if not self._dlq_subscription_path:
            return
        try:
            response = self._subscriber.pull(
                request={
                    "subscription": self._dlq_subscription_path,
                    "max_messages": 100,
                    "return_immediately": True,
                }
            )
        except Exception:
            logger.exception(
                "DLQ depth sample failed subscription=%s",
                self._config.dlq_subscription,
            )
            return
        count = len(response.received_messages)
        with self._metrics_lock:
            self._dlq_undelivered_messages = count
        if count > 0:
            logger.warning(
                "DLQ has undelivered messages count=%d subscription=%s",
                count,
                self._config.dlq_subscription,
            )
            ack_ids = [msg.ack_id for msg in response.received_messages]
            if ack_ids:
                self._subscriber.modify_ack_deadline(
                    request={
                        "subscription": self._dlq_subscription_path,
                        "ack_ids": ack_ids,
                        "ack_deadline_seconds": self._config.ack_extension_seconds,
                    }
                )

    def _pull_messages(self, max_messages: int) -> list[PulledMessage]:
        response = self._subscriber.pull(
            request={
                "subscription": self._subscription_path,
                "max_messages": max_messages,
            }
        )
        result: list[PulledMessage] = []
        for received in response.received_messages:
            self._subscriber.modify_ack_deadline(
                request={
                    "subscription": self._subscription_path,
                    "ack_ids": [received.ack_id],
                    "ack_deadline_seconds": self._config.ack_extension_seconds,
                }
            )
            result.append(
                PulledMessage(
                    ack_id=received.ack_id,
                    message_id=received.message.message_id,
                    data=received.message.data,
                )
            )
        return result

    async def _handle_message(self, pulled: PulledMessage) -> None:
        try:
            payload = json.loads(pulled.data.decode("utf-8"))
        except json.JSONDecodeError:
            logger.error("Invalid Pub/Sub payload; acking to drop")
            self._ack(pulled.ack_id)
            return

        bucket = payload.get("bucket")
        object_name = payload.get("name")
        generation = payload.get("generation")
        if not bucket or not object_name or generation is None:
            logger.error("Missing GCS fields in payload; acking to drop")
            self._ack(pulled.ack_id)
            return

        version_key = document_version_id(bucket, object_name, generation)

        with self._lock:
            if version_key in self._in_flight:
                logger.info(
                    "Skipping duplicate in-flight document_version_id=%s",
                    version_key,
                )
                return

        existing = await self._prefect.find_running_flow_run(version_key)
        if existing:
            logger.info(
                "Prefect run already active document_version_id=%s flow_run_id=%s",
                version_key,
                existing,
            )
            return

        parameters = {
            "bucket": bucket,
            "object_name": object_name,
            "generation": str(generation),
            "pubsub_message_id": pulled.message_id,
        }
        try:
            flow_run_id = await self._prefect.create_flow_run(parameters)
        except Exception:
            logger.exception(
                "Failed to create Prefect run document_version_id=%s",
                version_key,
            )
            self._record_failure(
                reason="prefect_create_failed",
                document_version_id=version_key,
                pubsub_message_id=pulled.message_id,
            )
            self._nack(pulled.ack_id)
            return

        self._record_run_started()
        logger.info(
            "Started Prefect run document_version_id=%s prefect_flow_run_id=%s pubsub_message_id=%s",
            version_key,
            flow_run_id,
            pulled.message_id,
        )
        with self._lock:
            self._in_flight[version_key] = InFlightRun(
                ack_id=pulled.ack_id,
                pubsub_message_id=pulled.message_id,
                document_version_id=version_key,
                prefect_flow_run_id=flow_run_id,
            )

    async def _poll_in_flight(self) -> None:
        with self._lock:
            items = list(self._in_flight.items())

        for version_key, run in items:
            await self._extend_ack(run.ack_id)
            state = await self._prefect.get_flow_run_state(run.prefect_flow_run_id)
            elapsed = time.monotonic() - run.started_at
            if state not in TERMINAL_STATES:
                if elapsed > self._config.flow_timeout_seconds:
                    self._record_failure(
                        reason="flow_timeout",
                        document_version_id=run.document_version_id,
                        pubsub_message_id=run.pubsub_message_id,
                        prefect_flow_run_id=run.prefect_flow_run_id,
                    )
                    self._nack(run.ack_id)
                    self._remove_in_flight(version_key)
                continue

            if state in SUCCESS_STATES:
                logger.info(
                    "Flow completed document_version_id=%s prefect_flow_run_id=%s",
                    version_key,
                    run.prefect_flow_run_id,
                )
                self._ack(run.ack_id)
            else:
                self._record_failure(
                    reason=f"flow_{state.lower()}",
                    document_version_id=run.document_version_id,
                    pubsub_message_id=run.pubsub_message_id,
                    prefect_flow_run_id=run.prefect_flow_run_id,
                )
                self._nack(run.ack_id)
            self._remove_in_flight(version_key)

    async def _extend_ack(self, ack_id: str) -> None:
        await asyncio.to_thread(
            self._subscriber.modify_ack_deadline,
            request={
                "subscription": self._subscription_path,
                "ack_ids": [ack_id],
                "ack_deadline_seconds": self._config.ack_extension_seconds,
            },
        )

    def _ack(self, ack_id: str) -> None:
        self._subscriber.acknowledge(
            request={
                "subscription": self._subscription_path,
                "ack_ids": [ack_id],
            }
        )

    def _nack(self, ack_id: str) -> None:
        self._subscriber.modify_ack_deadline(
            request={
                "subscription": self._subscription_path,
                "ack_ids": [ack_id],
                "ack_deadline_seconds": 0,
            }
        )

    def _remove_in_flight(self, version_key: str) -> None:
        with self._lock:
            self._in_flight.pop(version_key, None)
