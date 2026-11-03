from __future__ import annotations

import atexit
from dataclasses import dataclass, field
from logging import getLogger
from typing import BinaryIO, Literal
from urllib.parse import urlencode

from testcontainers.docker_client_factory import (
    DEFAULT_LABELS,
    DockerClientFactory,
    SESSION_ID,
    TESTCONTAINERS_SESSION_ID_LABEL,
)

LOGGER = getLogger(__name__)

MARKER_LABELS = {TESTCONTAINERS_SESSION_ID_LABEL: SESSION_ID}

# DEATH_NOTE = DEFAULT_LABELS | MARKER_LABELS
DEATH_NOTE: list[list[tuple[Literal["label"], str]]] = [
    [("label", f"{k}={v}") for k, v in (DEFAULT_LABELS | MARKER_LABELS).items()]
]

instance: ResourceReaper | None = None


@dataclass
class ResourceReaper:
    _docker_client: DockerClient = field(default_factory=DockerClientFactory.lazy_client)
    _registered_containers: dict[str, str] = field(default_factory=dict)
    _registered_networks: set[str] = field(default_factory=set)
    _registered_images: set[str] = field(default_factory=set)
    _hook_is_set: bool = field(default=False)

    # def __init__(self):
    #     self.docker_client = DockerClientFactory.lazy_client()
    #     self.registered

    @staticmethod
    def instance() -> ResourceReaper:
        global instance

        if instance is None:
            use_ryuk: bool = True
            if use_ryuk:
                from testcontainers.utility.ryuk_resource_reaper import RyukResourceReaper

                instance = RyukResourceReaper()
            else:
                from testcontainers.utility.hook_resource_reaper import HookResourceReaper

                instance = HookResourceReaper()
        return instance

    def perform_cleanup(self) -> None:
        for registered_container, rci in self._registered_containers.items():
            self.remove_container(registered_container, rci)
        for registered_network in self._registered_networks:
            self.remove_network(registered_network)
        for registered_image in self._registered_images:
            self.remove_image(registered_image)

    @staticmethod
    def _register_filter_for_cleanup(filter_: list[tuple[Literal["label"], str]]) -> None:
        DEATH_NOTE.append(filter_)

    def register_labels_filter_for_cleanup(self, labels: dict[str, str]) -> None:
        self._register_filter_for_cleanup([("label", f"{k}={v}") for k, v in labels.items()])

    # def register_container_for_cleanup(self, container_id: str, image_name: str):
    # def stop_and_remove_container(self, container_id: str):
    # def stop_and_remove_container_and_image(self, container_id: str, image_name: str):

    def remove_container(self, container_id: str, image_name: str):
        def log_fail(ex: Exception) -> None:
            LOGGER.debug(
                "Error encountered when checking container for shutdown (ID: %s) - "
                "it may not have been stopped, or may already be stopped. Root cause: %s",
                container_id,
                ex,
                exc_info=(type(ex), ex, ex.__traceback__),
            )

        try:
            container_info = self._docker_client.inspect_container_cmd(container_id).exec()
            running = container_info.state is not None and container_info.state.running
        except FileNotFoundError:
            LOGGER.debug("Was going to stop container but it apparently no longer exists: %s", container_id)
            return
        except APIException as e:
            log_fail(e)
            return

        if running:
            try:
                LOGGER.debug("Stopping container: %s", container_id)
                self._docker_client.kill_container_cmd(container_id).exec()
                LOGGER.debug("Stopped container: %s", image_name)
            except APIException as e:
                log_fail(e)

        try:
            self._docker_client.inspect_container_cmd(container_id).exec()
        except APIException as e:
            LOGGER.debug("Was going to remove container but it apparently no longer exists: %s", container_id)
            return

        try:
            LOGGER.debug("Removing container: {}", container_id)
            self._docker_client.remove_container_cmd(container_id).with_remove_volumes(True).with_force(True).exec()
            LOGGER.debug("Removed container and associated volume(s): {}", image_name)
        except APIException as e:
            log_fail(e)

    # def register_network_id_for_cleanup(self, network_id: str) -> None:
    # def remove_network_by_id(self, network_id: str) -> None:

    def remove_network(self, network_id: str) -> None:
        try:
            try:
                networks: list[Network] = self._docker_client.list_networks().with_id_filter(network_id).exec()
            except APIException as e:
                LOGGER.debug(
                    "Error encountered when looking up network for removal (name: %s) - it may not have been removed",
                    network_id,
                    exc_info=True,
                )
                return

            for network in networks:
                try:
                    self._docker_client.remove_network_cmd(network_id).exec()
                    self._registered_networks.remove(network_id)
                    LOGGER.debug("Removed network: %s", network_id)
                except APIException:
                    LOGGER.debug(
                        "Error encountered removing network (name: %s) - it may not have been removed",
                        network.name,
                        exc_info=True,
                    )

        finally:
            self._registered_networks.remove(network_id)

    def unregister_network(self, identifier: str) -> None:
        self._registered_networks.remove(identifier)

    def unregister_container(self, identifier: str) -> None:
        self._registered_containers.pop(identifier, None)

    def register_image_for_cleanup(self, docker_image_name: str) -> None:
        self._set_hook()
        self._registered_images.add(docker_image_name)

    def remove_image(self, docker_image_name: str) -> None:
        LOGGER.debug("Removing image tagged %s", docker_image_name)
        try:
            self._docker_client.remove_image_cmd(docker_image_name).with_force(True).exec()
        except APIException:
            LOGGER.warning("Unable to delete image %s", docker_image_name, exc_info=True)

    def _set_hook(self) -> None:
        if not self._hook_is_set:
            self._hook_is_set = True

            atexit.register(self.perform_cleanup)

    def get_labels(self) -> dict[str, str]:
        return MARKER_LABELS

    def register(self) -> None:
        pass

    def init(self) -> None:
        pass


class FilterRegistry:
    ACKNOWLEDGMENT: str = "ACK"

    def __init__(
        self,
        ryuk_input_stream: BinaryIO,
        ryuk_output_stream: BinaryIO,
    ) -> None:
        self.in_: BinaryIO = ryuk_input_stream
        self.out: BinaryIO = ryuk_output_stream

    def register(self, filters: list[tuple[str, str]]) -> bool:
        query: str = urlencode(filters)

        LOGGER.debug("Sending %r to Ryuk", query)

        self.out.write(query.encode("utf-8"))
        self.out.write(b"\n")
        self.out.flush()

        return self._wait_for_acknowledgment()

    def _wait_for_acknowledgment(self) -> bool:
        while True:
            line: bytes = self.in_.readline()

            if not line:
                return False

            value: str = line.decode("utf-8").rstrip("\r\n")

            if value.casefold() == self.ACKNOWLEDGMENT.casefold():
                return True
