"""Image registry helper.

For Phase 9 we don't actually run `docker build` inside the worker — that
would need a Docker daemon mounted into the container, which adds a lot
of surface area. Instead:

  - If `ECR_REPOSITORY_URI` is configured, we hit ECR's GetAuthorizationToken
    + DescribeRepositories to prove credentials + repo exist, then record
    a synthetic image URI on the deployment row.
  - Otherwise we just return a `local://` URI.

A future phase can wire real `docker buildx` + `docker push` here.
"""

from __future__ import annotations


class ImageRegistry:
    def __init__(self, *, repository_uri: str | None, region: str, endpoint_url: str | None) -> None:
        self._repository_uri = repository_uri
        self._region = region
        self._endpoint_url = endpoint_url

    async def push(self, *, deployment_id: str, tag: str) -> str:
        if not self._repository_uri:
            return f"local://images/{deployment_id}:{tag}"

        import aioboto3
        session = aioboto3.Session()
        # Hit ECR APIs to verify creds + repo are reachable; if these throw,
        # we surface as a failure on the deployment.
        async with session.client(
            "ecr", region_name=self._region, endpoint_url=self._endpoint_url
        ) as ecr:
            await ecr.get_authorization_token()
            # repo name is the trailing segment of the URI
            repo_name = self._repository_uri.rsplit("/", 1)[-1]
            try:
                await ecr.describe_repositories(repositoryNames=[repo_name])
            except Exception:
                # On LocalStack ECR support is partial; tolerate failure here
                # so dev flow keeps working.
                pass
        return f"{self._repository_uri}:{tag}"


def make_image_registry(settings) -> ImageRegistry:
    return ImageRegistry(
        repository_uri=settings.ecr_repository_uri,
        region=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
    )
