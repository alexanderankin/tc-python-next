import sys
import threading
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

from testcontainers.containers.compose_delegate import ComposeDelegate
from testcontainers.lifecycle.startable import Startable
from testcontainers.utility.docker_image_name import DockerImageName

COMPOSE_EXECUTABLE = "docker.exe" if sys.platform.startswith("win") else "docker"
DEFAULT_IMAGE_NAME = DockerImageName.parse("docker")
MUTEX = threading.Lock()


# noinspection abstract-class
@dataclass(unsafe_hash=True)
class ComposeContainer(Startable):
    scaling_preferences: dict[str, int] = field(default_factory=dict)
    local_compose: bool = field(default=False)
    pull: bool = field(default=True)
    build: bool = field(default=False)
    options: set[str] = field(default_factory=set)
    tail_child_containers: bool = field(default=False)
    services: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    remove_images: Optional["RemoveImages"] = field(default=None)
    remove_volumes: bool = field(default=True)
    compose_delegate: ComposeDelegate | None = None
    project: str | None = None
    files_in_directory: list[str] | None = field(default_factory=list)

    def start(self) -> None:
        with MUTEX:
            self.compose_delegate.register

    def stop(self) -> None:
        pass


class RemoveImages(StrEnum):
    """Remove all images used by any service."""

    ALL = "all"

    """Remove only images that don't have a custom tag set by the `image` field."""
    LOCAL = "local"
