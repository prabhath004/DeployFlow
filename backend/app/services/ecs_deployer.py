"""ECS Fargate deployment service."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.core.config import Settings


LogCallback = Callable[[str], Awaitable[None]]


class EcsDeployer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def deploy(
        self,
        *,
        project_id: str,
        deployment_id: str,
        image_uri: str,
        log: LogCallback,
    ) -> str:
        if self.settings.deploy_backend != "ecs":
            await log("ECS deploy backend is disabled; skipping real compute deploy")
            return ""

        missing = [
            name
            for name, value in {
                "ECS_CLUSTER_NAME": self.settings.ecs_cluster_name,
                "ECS_SUBNET_IDS": self.settings.ecs_subnet_ids,
                "ECS_SECURITY_GROUP_ID": self.settings.ecs_security_group_id,
                "ECS_TASK_EXECUTION_ROLE_ARN": self.settings.ecs_task_execution_role_arn,
                "ECS_APP_LOG_GROUP": self.settings.ecs_app_log_group,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"ECS deploy backend missing settings: {', '.join(missing)}")

        import aioboto3

        session = aioboto3.Session()
        family = _ecs_name(f"deployflow-{project_id}")
        service_name = family
        container_name = "app"
        port = self.settings.deployed_app_port
        subnets = [
            s.strip()
            for s in self.settings.ecs_subnet_ids.split(",")
            if s.strip()
        ]

        await log(f"Registering ECS task definition {family}")
        async with session.client("ecs", region_name=self.settings.aws_region) as ecs:
            task_def = await ecs.register_task_definition(
                family=family,
                networkMode="awsvpc",
                requiresCompatibilities=["FARGATE"],
                cpu=str(self.settings.ecs_task_cpu),
                memory=str(self.settings.ecs_task_memory),
                executionRoleArn=self.settings.ecs_task_execution_role_arn,
                runtimePlatform={
                    "operatingSystemFamily": "LINUX",
                    "cpuArchitecture": self.settings.ecs_cpu_architecture,
                },
                containerDefinitions=[
                    {
                        "name": container_name,
                        "image": image_uri,
                        "essential": True,
                        "portMappings": [
                            {
                                "containerPort": port,
                                "hostPort": port,
                                "protocol": "tcp",
                            }
                        ],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": self.settings.ecs_app_log_group,
                                "awslogs-region": self.settings.aws_region,
                                "awslogs-stream-prefix": "deployflow",
                            },
                        },
                    }
                ],
            )
            task_def_arn = task_def["taskDefinition"]["taskDefinitionArn"]

            if await _service_exists(
                ecs,
                cluster=self.settings.ecs_cluster_name,
                service_name=service_name,
            ):
                await log(f"Updating ECS service {service_name}")
                await ecs.update_service(
                    cluster=self.settings.ecs_cluster_name,
                    service=service_name,
                    taskDefinition=task_def_arn,
                    desiredCount=1,
                    forceNewDeployment=True,
                )
            else:
                await log(f"Creating ECS service {service_name}")
                await ecs.create_service(
                    cluster=self.settings.ecs_cluster_name,
                    serviceName=service_name,
                    taskDefinition=task_def_arn,
                    desiredCount=1,
                    launchType="FARGATE",
                    networkConfiguration={
                        "awsvpcConfiguration": {
                            "subnets": subnets,
                            "securityGroups": [self.settings.ecs_security_group_id],
                            "assignPublicIp": "ENABLED",
                        }
                    },
                )

            await log("Waiting for ECS task to start")
            task_arn = await _wait_for_running_task(
                ecs,
                cluster=self.settings.ecs_cluster_name,
                service_name=service_name,
            )
            eni_id = await _task_network_interface(
                ecs,
                cluster=self.settings.ecs_cluster_name,
                task_arn=task_arn,
            )

        async with session.client("ec2", region_name=self.settings.aws_region) as ec2:
            public_ip = await _wait_for_public_ip(ec2, eni_id=eni_id)

        url = f"http://{public_ip}:{port}"
        await log(f"ECS service is live: {url}")
        return url


async def _service_exists(ecs, *, cluster: str, service_name: str) -> bool:
    resp = await ecs.describe_services(cluster=cluster, services=[service_name])
    failures = resp.get("failures") or []
    services = resp.get("services") or []
    if failures and not services:
        return False
    return bool(services and services[0].get("status") != "INACTIVE")


async def _wait_for_running_task(
    ecs,
    *,
    cluster: str,
    service_name: str,
    timeout_seconds: int = 420,
) -> str:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    last_status = "unknown"
    while asyncio.get_event_loop().time() < deadline:
        task_list = await ecs.list_tasks(
            cluster=cluster,
            serviceName=service_name,
            desiredStatus="RUNNING",
            maxResults=10,
        )
        task_arns = task_list.get("taskArns") or []
        if task_arns:
            tasks = await ecs.describe_tasks(cluster=cluster, tasks=task_arns)
            for task in tasks.get("tasks") or []:
                last_status = task.get("lastStatus", last_status)
                if task.get("lastStatus") == "RUNNING":
                    return task["taskArn"]
        await asyncio.sleep(5)
    raise RuntimeError(f"ECS task did not reach RUNNING; last status: {last_status}")


async def _task_network_interface(ecs, *, cluster: str, task_arn: str) -> str:
    tasks = await ecs.describe_tasks(cluster=cluster, tasks=[task_arn])
    task = tasks["tasks"][0]
    for attachment in task.get("attachments") or []:
        for detail in attachment.get("details") or []:
            if detail.get("name") == "networkInterfaceId":
                return detail["value"]
    raise RuntimeError("ECS task did not expose a network interface ID")


async def _wait_for_public_ip(ec2, *, eni_id: str, timeout_seconds: int = 120) -> str:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while asyncio.get_event_loop().time() < deadline:
        resp = await ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
        eni = resp["NetworkInterfaces"][0]
        public_ip = (eni.get("Association") or {}).get("PublicIp")
        if public_ip:
            return public_ip
        await asyncio.sleep(3)
    raise RuntimeError("ECS task did not receive a public IP")


def _ecs_name(value: str) -> str:
    out = []
    for char in value:
        out.append(char if char.isalnum() or char in "-_" else "-")
    return "".join(out)[:255]
