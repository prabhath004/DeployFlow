"""Build and push deployment images.

In AWS mode this is real: clone the project repository, build its Dockerfile
with the local Docker engine, log in to ECR, and push the tag. Local-only mode
still returns a local placeholder so the $0 compose path remains lightweight.
"""

from __future__ import annotations

import asyncio
import base64
import re
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path


LogCallback = Callable[[str], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class ImageBuildResult:
    image_uri: str
    commit_sha: str | None


class ImageRegistry:
    def __init__(
        self,
        *,
        repository_uri: str | None,
        region: str,
        endpoint_url: str | None,
        platform: str,
    ) -> None:
        self._repository_uri = repository_uri
        self._region = region
        self._endpoint_url = endpoint_url
        self._platform = platform

    async def build_and_push(
        self,
        *,
        repository_url: str,
        branch: str,
        deployment_id: str,
        tag: str,
        log: LogCallback,
    ) -> ImageBuildResult:
        if not self._repository_uri:
            image_uri = f"local://images/{deployment_id}:{tag}"
            await log(f"ECR is not configured; using local image placeholder: {image_uri}")
            return ImageBuildResult(image_uri=image_uri, commit_sha=None)

        image_uri = f"{self._repository_uri}:{tag}"

        with tempfile.TemporaryDirectory(prefix=f"deployflow-{deployment_id}-") as tmp:
            repo_dir = Path(tmp) / "src"
            await log(f"Cloning {repository_url} branch {branch}")
            await _run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    branch,
                    repository_url,
                    str(repo_dir),
                ],
                log=log,
            )

            commit_sha = (
                await _run_capture(["git", "-C", str(repo_dir), "rev-parse", "HEAD"])
            ).strip()
            await _ensure_build_recipe(repo_dir, log)

            await self._docker_login(log)

            await log(f"Building Docker image for {self._platform}: {image_uri}")
            await _run(
                [
                    "docker",
                    "build",
                    "--platform",
                    self._platform,
                    "-t",
                    image_uri,
                    str(repo_dir),
                ],
                log=log,
            )

            await log(f"Pushing image to ECR: {image_uri}")
            await _run(["docker", "push", image_uri], log=log)

        return ImageBuildResult(image_uri=image_uri, commit_sha=commit_sha)

    async def _docker_login(self, log: LogCallback) -> None:
        import aioboto3

        session = aioboto3.Session()
        async with session.client(
            "ecr", region_name=self._region, endpoint_url=self._endpoint_url
        ) as ecr:
            await ecr.describe_repositories(
                repositoryNames=[self._repository_uri.rsplit("/", 1)[-1]]
            )
            auth = await ecr.get_authorization_token()

        auth_data = auth["authorizationData"][0]
        username, password = base64.b64decode(
            auth_data["authorizationToken"]
        ).decode("utf-8").split(":", 1)
        registry_url = auth_data["proxyEndpoint"]
        await log(f"Logging in to ECR registry {registry_url}")
        await _run(
            ["docker", "login", "--username", username, "--password-stdin", registry_url],
            input_text=password,
            log=log,
            redact=[password],
        )


def safe_image_tag(branch: str, deployment_id: str) -> str:
    branch_part = re.sub(r"[^A-Za-z0-9_.-]+", "-", branch).strip(".-") or "main"
    return f"{branch_part[:80]}-{deployment_id[-12:]}"


async def _ensure_build_recipe(repo_dir: Path, log: LogCallback) -> None:
    if (repo_dir / "Dockerfile").exists():
        await log("Found root Dockerfile")
        return

    if (repo_dir / "index.html").exists():
        await log("No Dockerfile found; detected static site from root index.html")
        (repo_dir / "Dockerfile").write_text(
            "\n".join(
                [
                    "FROM python:3.13-alpine",
                    "WORKDIR /app",
                    "COPY . .",
                    "EXPOSE 8000",
                    'CMD ["python", "-m", "http.server", "8000", "--bind", "0.0.0.0"]',
                    "",
                ]
            )
        )
        dockerignore = repo_dir / ".dockerignore"
        existing = dockerignore.read_text() if dockerignore.exists() else ""
        additions = ["Dockerfile", ".git", ".DS_Store", "node_modules", "dist", "build"]
        merged = existing.splitlines()
        for item in additions:
            if item not in merged:
                merged.append(item)
        dockerignore.write_text("\n".join(merged).strip() + "\n")
        await log("Generated static-site Dockerfile for port 8000")
        return

    raise RuntimeError(
        "No root Dockerfile found, and DeployFlow could not infer a build type. "
        "Supported zero-config fallback right now: static site with root index.html."
    )


async def _run(
    args: list[str],
    *,
    log: LogCallback,
    input_text: str | None = None,
    redact: list[str] | None = None,
) -> None:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if input_text is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    if input_text is not None:
        assert proc.stdin is not None
        proc.stdin.write(input_text.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()

    assert proc.stdout is not None
    async for raw in proc.stdout:
        line = raw.decode("utf-8", errors="replace").rstrip()
        if line:
            for secret in redact or []:
                line = line.replace(secret, "***")
            await log(line)

    code = await proc.wait()
    if code != 0:
        raise RuntimeError(f"Command failed ({code}): {_format_command(args)}")


async def _run_capture(args: list[str]) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Command failed ({proc.returncode}): {_format_command(args)} {detail}")
    return stdout.decode("utf-8", errors="replace")


def _format_command(args: list[str]) -> str:
    return " ".join(args[:4] + (["..."] if len(args) > 4 else []))


def make_image_registry(settings) -> ImageRegistry:
    return ImageRegistry(
        repository_uri=settings.ecr_repository_uri,
        region=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        platform=settings.deploy_image_platform,
    )
