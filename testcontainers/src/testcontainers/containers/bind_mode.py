import enum

from testcontainers.docker_client.docker.access_mode import AccessMode


class BindMode(enum.Enum):
    ro = AccessMode.ro
    rw = AccessMode.rw
