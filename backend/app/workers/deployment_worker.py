"""Deployment worker.

Run as: `python -m app.workers.deployment_worker`

Loop:
  1. Reclaim any orphan messages (left behind by a crashed worker).
  2. Block-consume one message from the deployments stream.
  3. Process it: advance state through RUNNING -> BUILDING -> DEPLOYING -> SUCCEEDED|FAILED.
  4. Ack the message.
  5. Heartbeat to Redis so the API knows we're alive.

Every status write goes through DeploymentService._set_status, which goes
through the state machine. Logs are written to Postgres AND published to
Redis pub/sub so SSE clients can tail them live.

For Phase 6, the actual "deploy" is simulated (sleeps + log lines). Phase 9
will replace the simulation with a real Docker build + ECR push.
"""

from __future__ import annotations

import asyncio
import os
import random
import signal
import socket
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.database import dispose_engine, get_engine, init_engine
from app.db.redis import dispose_redis, get_redis, init_redis
from app.models.enums import (
    DeploymentStatus,
    LogLevel,
    WorkerStatus,
)
from app.repositories.deployment_repo import DeploymentRepo
from app.repositories.log_repo import LogRepo
from app.repositories.project_repo import ProjectRepo
from app.observability import metrics as obs_metrics
from app.observability.logging import setup_logging
from app.observability.tracing import setup_tracing, tracer
from app.services.artifact_store import ArtifactStore, make_artifact_store
from app.services.cache_service import CacheService
from app.services.deployment_service import DeploymentService
from app.services.heartbeat_service import HeartbeatService
from app.services.image_registry import ImageRegistry, make_image_registry
from app.services.log_stream_service import LogStreamService
from app.services.queue_service import QueueMessage, RedisStreamQueue, make_queue
from sqlalchemy.ext.asyncio import async_sessionmaker

# Sentinel set by SIGTERM/SIGINT handlers. Loop checks it between jobs.
_stop_event = asyncio.Event()


def _install_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    def _handler() -> None:
        print("[worker] received signal, draining...", flush=True)
        _stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handler)


async def _emit(
    *,
    session: AsyncSession,
    stream: LogStreamService,
    deployment_id: str,
    level: LogLevel,
    message: str,
) -> None:
    """Write a log line to Postgres AND publish it to Redis pub/sub."""
    await LogRepo(session).append(
        deployment_id=deployment_id,
        message=message,
        level=level,
        source="worker",
    )
    await session.commit()
    await stream.publish(
        deployment_id=deployment_id,
        level=level.value,
        source="worker",
        message=message,
    )


async def _process_message(
    *,
    msg: QueueMessage,
    settings: Settings,
    sessionmaker: async_sessionmaker[AsyncSession],
    stream: LogStreamService,
    artifacts: ArtifactStore,
    registry: ImageRegistry,
) -> None:
    deployment_id = msg.body.get("deployment_id")
    if not isinstance(deployment_id, str):
        print(f"[worker] dropping malformed job: {msg.body}", flush=True)
        return

    async with sessionmaker() as session:
        service = DeploymentService(
            session,
            DeploymentRepo(session),
            ProjectRepo(session),
            cache=CacheService(get_redis(), settings),
        )
        deployment = await DeploymentRepo(session).get(deployment_id)
        if deployment is None:
            print(f"[worker] deployment row missing for {deployment_id}", flush=True)
            return

        # Idempotency: if we crash mid-job and the message is redelivered,
        # the deployment may already be terminal. Skip it.
        current = DeploymentStatus(deployment.status)
        if current in {
            DeploymentStatus.SUCCEEDED,
            DeploymentStatus.FAILED,
            DeploymentStatus.CANCELLED,
        }:
            print(f"[worker] {deployment_id} already terminal ({current}), skipping", flush=True)
            return

        try:
            await service._set_status(deployment, DeploymentStatus.RUNNING)
            await session.commit()
            await _emit(
                session=session, stream=stream, deployment_id=deployment_id,
                level=LogLevel.INFO, message="Deployment started",
            )

            await service._set_status(deployment, DeploymentStatus.BUILDING)
            await session.commit()
            await _emit(
                session=session, stream=stream, deployment_id=deployment_id,
                level=LogLevel.INFO, message="Building image",
            )
            await asyncio.sleep(random.uniform(0.5, 1.5))  # simulated build

            # Phase 9: "push" the image to the configured registry and stamp the URI.
            image_tag = f"{deployment.branch}-{deployment.id[-12:]}"
            image_uri = await registry.push(deployment_id=deployment.id, tag=image_tag)
            deployment.image_uri = image_uri
            await _emit(
                session=session, stream=stream, deployment_id=deployment_id,
                level=LogLevel.INFO, message=f"Pushed image: {image_uri}",
            )

            await service._set_status(deployment, DeploymentStatus.DEPLOYING)
            await session.commit()
            await _emit(
                session=session, stream=stream, deployment_id=deployment_id,
                level=LogLevel.INFO, message="Deploying",
            )
            await asyncio.sleep(random.uniform(0.5, 1.5))  # simulated deploy

            # 10% simulated failure rate for demos.
            if random.random() < 0.1:
                raise RuntimeError("simulated deploy failure")

            await service._set_status(deployment, DeploymentStatus.SUCCEEDED)
            await session.commit()
            await _emit(
                session=session, stream=stream, deployment_id=deployment_id,
                level=LogLevel.INFO, message="Deployment succeeded",
            )
        except Exception as exc:
            deployment.error_message = str(exc)[:500]
            try:
                await service._set_status(deployment, DeploymentStatus.FAILED)
                await session.commit()
            except Exception:
                # State machine refused the transition (e.g. user cancelled).
                pass
            await _emit(
                session=session, stream=stream, deployment_id=deployment_id,
                level=LogLevel.ERROR, message=f"Deployment failed: {exc}",
            )
        finally:
            # Phase 9: archive the full log to S3 (or whatever ArtifactStore
            # is configured). Best-effort — don't fail the deployment on
            # an upload hiccup.
            try:
                from app.repositories.log_repo import LogRepo
                logs = await LogRepo(session).list_for_deployment(deployment_id)
                text = "\n".join(
                    f"{l.created_at.isoformat()} | {l.level:5s} | {l.source} | {l.message}"
                    for l in logs
                )
                uri = await artifacts.upload_text(
                    key=f"{deployment_id}.log",
                    body=text,
                    content_type="text/plain",
                )
                if not uri.startswith("noop://"):
                    print(f"[worker] archived logs for {deployment_id} → {uri}", flush=True)
            except Exception as exc:
                print(f"[worker] log upload failed for {deployment_id}: {exc}", flush=True)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    setup_tracing("deployflow-worker")
    obs_metrics.setup_metrics("deployflow-worker")
    init_engine(settings)
    init_redis(settings)
    worker_id = f"worker-{socket.gethostname()}-{os.getpid()}"
    print(f"[worker] starting {worker_id}", flush=True)

    queue = make_queue(settings, get_redis())
    if isinstance(queue, RedisStreamQueue):
        await queue.ensure_group()

    stream = LogStreamService(get_redis())
    heartbeat = HeartbeatService(get_redis(), settings)
    artifacts = make_artifact_store(settings)
    registry = make_image_registry(settings)
    await heartbeat.touch(worker_id, WorkerStatus.IDLE.value)

    engine = get_engine()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    _install_signal_handlers(asyncio.get_running_loop())

    last_orphan_check = 0.0
    try:
        while not _stop_event.is_set():
            # Periodically reclaim stale messages another worker may have died on.
            now = asyncio.get_event_loop().time()
            if now - last_orphan_check > 30:
                orphans = await queue.reclaim_orphans(
                    consumer=worker_id, idle_ms=60_000
                )
                for o in orphans:
                    await _process_message(
                        msg=o, settings=settings,
                        sessionmaker=sessionmaker, stream=stream,
                        artifacts=artifacts, registry=registry,
                    )
                    await queue.ack(o.message_id)
                last_orphan_check = now

            await heartbeat.touch(worker_id, WorkerStatus.IDLE.value)
            msg = await queue.consume(consumer=worker_id, block_ms=2000)
            if msg is None:
                continue
            await heartbeat.touch(worker_id, WorkerStatus.BUSY.value)
            try:
                await _process_message(
                    msg=msg, settings=settings,
                    sessionmaker=sessionmaker, stream=stream,
                    artifacts=artifacts, registry=registry,
                )
                await queue.ack(msg.message_id)
            except Exception as exc:
                print(f"[worker] unhandled exception: {exc}", flush=True)
                # Don't ack — XAUTOCLAIM will redeliver after idle_ms.
    finally:
        await heartbeat.touch(worker_id, WorkerStatus.DRAINING.value)
        print(f"[worker] {worker_id} stopped", flush=True)
        await dispose_redis()
        await dispose_engine()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
