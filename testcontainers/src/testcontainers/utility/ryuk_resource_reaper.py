from dataclasses import dataclass, field

from testcontainers.utility.resource_reaper import ResourceReaper
from testcontainers.utility.testcontainers_configuration import TestcontainersConfiguration


@dataclass
class RyukResourceReaper(ResourceReaper):
    _started: bool = field(default=False)
    _ryuk_container: RyukContainer | None = field(default=False, repr=False)

    def init(self) -> None:
        (TestcontainersConfiguration.get_instance())
