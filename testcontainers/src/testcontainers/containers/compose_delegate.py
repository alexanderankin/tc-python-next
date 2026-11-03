from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable

from testcontainers.containers.output.output_frame import OutputFrame
from testcontainers.utility.docker_image_name import DockerImageName
from testcontainers.utility.resource_reaper import ResourceReaper


@dataclass
class ComposeDelegate:
    compose_version: ComposeVersion
    compose_separator: str
    docker_client: DockerClient
    compose_files: list[str]
    docker_compose_files: DockerComposeFiles
    identifier: str
    project: str
    executable: str
    default_image_name: DockerImageName
    next_ambassador_port: int
    ambassador_port_mappings: dict[str, dict[int, int]]
    log_consumers: dict[str, list[Callable[[OutputFrame], None]]]
    ambassador_container: SocatContainer
    service_instance_map: dict[str, ComposeServiceWaitStrategyTarget]
    wait_strategy_map: dict[str, WaitAllStrategy]

    @staticmethod
    def of(
        compose_version: ComposeVersion,
        compose_files: list[Path],
        identifier: str,
        executable: str,
        default_image_name: DockerImageName,
    ) -> ComposeDelegate:
        compose_delegate = ComposeDelegate(
            compose_version=compose_version,
            compose_separator=compose_version.value,
            docker_client=DockerClientFactory.lazy_client(),
            compose_files=compose_files,
            docker_compose_files=DockerComposeFiles(compose_files),
            identifier=identifier.lower(),
            executable=executable,
            default_image_name=default_image_name,
        )
        compose_delegate.project = compose_delegate.random_project_id()
        return compose_delegate

    def pull_images(self) -> None:
        pass

    def create_services(
        self,
        local_compose: bool,
        build: bool,
        options: set[str],
        services: list[str],
        scaling_preferences: dict[str, int],
        env: dict[str, str],
        file_copy_inclusions: list[str],
    ) -> None:
        pass

    def wait_until_service_started(self, tail_child_containers: bool) -> None:
        pass

    def create_service_instance(self, container: Container, tail_child_containers: bool) -> None:
        pass

    def wait_until_service_started_instance(
        self,
        service_name: str,
        service_instance: ComposeServiceWaitStrategyTarget,
    ) -> None:
        wait_all_strategy = self.wait_strategy_map.get(service_name)
        if wait_all_strategy is not None:
            wait_all_strategy.wait_until_ready(service_instance)

    def get_service_name_from_container(self) -> str:
        pass

    def run_with_compose(
        self, local_compose: bool, cmd: str, env: dict[str, str], file_copy_inclusions: list[str]
    ) -> None:
        assert self.compose_files is not None
        assert len(self.compose_files) != 0

        docker_compose: DockerCompose
        if local_compose:
            docker_compose = LocalDockerCompose(self.executable, self.compose_files, self.project)
        else:
            docker_compose = ContainerizedDockerCompose(
                self.executable, self.compose_files, self.project, file_copy_inclusions
            )

        docker_compose.with_command(cmd).with_env(env).invoke()

    def register_containers_for_shutdown(self) -> None:
        rr = ResourceReaper.instance()
        rr.register_labels_filter_for_cleanup({"com.docker.compose.project": self.project})

    # def _list_child_containers(self) -> list[Any]:

    def _start_ambassador_container(self) -> None:
        if self.ambassador_port_mappings is not None and len(self.ambassador_port_mappings) > 0:
            self.ambassador_container.start()


class ComposeVersion(StrEnum):
    V1 = "_"
    V2 = "-"
