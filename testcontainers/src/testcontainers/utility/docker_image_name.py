import re
from dataclasses import asdict, dataclass, field
from typing import ClassVar

from testcontainers.utility.versioning import Sha256Versioning, TagVersioning, Versioning


@dataclass(frozen=True)
class DockerImageName:
    ALPHA_NUMERIC: ClassVar[str] = "[a-z0-9]+"
    SEPARATOR: ClassVar[str] = "([.]|_{1,2}|-+)"
    REPO_NAME_PART: ClassVar[str] = ALPHA_NUMERIC + "(" + SEPARATOR + ALPHA_NUMERIC + ")*"
    REPO_NAME: ClassVar[re.Pattern[str]] = re.compile(REPO_NAME_PART + "(/" + REPO_NAME_PART + ")*")
    LIBRARY_PREFIX: ClassVar[str] = "library/"

    raw_name: str = field(compare=False, hash=False)
    registry: str
    repository: str
    versioning: Versioning
    compatible_substitute_for: DockerImageName | None = field(compare=False, hash=False)

    def get_unversioned_part(self) -> str:
        if self.registry != "":
            return f"{self.registry}/{self.repository}"
        return self.repository

    def get_version_part(self) -> str:
        if isinstance(self.versioning, Sha256Versioning):
            tag = self.versioning.tag
            if tag is not None:
                return tag
        return str(self.versioning)

    def get_digest(self) -> str | None:
        if isinstance(self.versioning, Sha256Versioning):
            return str(self.versioning)
        return None

    def as_canonical_name_string(self) -> str:
        if isinstance(self.versioning, Sha256Versioning):
            tag = self.versioning.tag
            if tag is not None:
                return f"{self.get_unversioned_part()}:{tag}@{self.versioning}"

        return f"{self.get_unversioned_part()}{self.versioning.separator}{self.get_version_part()}"

    def __str__(self) -> str:
        return self.as_canonical_name_string()

    def assert_valid(self) -> None:
        # return value ignored - this throws if registry is not a valid host:port string
        _GuavaHostAndPort.parse(self.registry)
        if DockerImageName.REPO_NAME.match(self.repository) is None:
            raise ValueError(f"{self.repository} is not a valid Docker image name (in {self.raw_name})")
        if not self.versioning.valid:
            raise ValueError(f"{self.versioning} is not a valid image versioning identifier (in {self.raw_name})")

    def with_tag(self, tag: str) -> DockerImageName:
        return self._with_versioning(TagVersioning(tag))

    def with_registry(self, registry: str) -> DockerImageName:
        return DockerImageName(asdict(self) | {"registry": registry})

    def with_repository(self, repository: str) -> DockerImageName:
        return DockerImageName(asdict(self) | {"repository": repository})

    def _with_versioning(self, versioning: Versioning) -> DockerImageName:
        return DockerImageName(asdict(self) | {"versioning": versioning})

    def _with_compatible_substitute_for(self, compatible_substitute_for: DockerImageName) -> DockerImageName:
        return DockerImageName(asdict(self) | {"compatible_substitute_for": compatible_substitute_for})

    def as_compatible_substitute_for_str(self, other: str) -> DockerImageName:
        return self.as_compatible_substitute_for_name(DockerImageName.parse(other))

    def as_compatible_substitute_for_name(self, other: DockerImageName) -> DockerImageName:
        return self._with_compatible_substitute_for(other)

    @staticmethod
    def parse(full_image_name: str) -> DockerImageName:
        raw_name = full_image_name
        slash_index = full_image_name.index("/") if "/" in full_image_name else -1
        slash_index_neg_1 = slash_index == -1

        if not slash_index_neg_1:
            before = full_image_name[0:slash_index]
            ip_host = "." in before or ":" in before or before == "localhost"
        else:
            ip_host = False

        if slash_index_neg_1 or ip_host:
            registry = ""
            remote_name = full_image_name
        else:
            registry = full_image_name[0:slash_index]
            remote_name = full_image_name[slash_index + 1 :]

        if "@sha256:" in remote_name:
            before_digest = remote_name.split("@sha256:")[0]
            if ":" in before_digest:
                repository = before_digest.split(":")[0]
                tag = before_digest.split(":", 1)[1]
                versioning = Sha256Versioning(remote_name.split("@sha256:")[1], tag)
            else:
                repository = before_digest
                versioning = Sha256Versioning(remote_name.split(":", 1)[1])
        elif ":" in remote_name:
            repository = remote_name.split(":")[0]
            versioning = TagVersioning(remote_name.split(":", 1)[1])
        else:
            repository = remote_name
            versioning = Versioning.ANY

        return DockerImageName(
            raw_name,
            registry,
            repository,
            versioning,
            compatible_substitute_for=None,
        )

    def is_compatible_with(self, other: DockerImageName) -> bool:
        if self.repository.startswith(DockerImageName.LIBRARY_PREFIX):
            final_image_name = self.repository
        else:
            final_image_name = DockerImageName.LIBRARY_PREFIX + self.repository

        image_with_library_prefix = DockerImageName.parse(final_image_name)
        if other == self or image_with_library_prefix == self:
            return True

        if self.compatible_substitute_for is None:
            return False

        return self.compatible_substitute_for.is_compatible_with(other)

    def assert_compatible_with(self, *any_others: DockerImageName) -> None:
        if len(any_others) == 0:
            raise ValueError("any_others parameter must be non-empty")

        for any_other in any_others:
            if self.is_compatible_with(any_other):
                return

        ex = any_others[0].raw_name
        raise ValueError(
            f"Failed to verify that image '{self.raw_name}' is a compatible substitute for '{ex}'. "
            f"This generally means that "
            "you are trying to use an image that Testcontainers has not been designed to use. If this is "
            "deliberate, and if you are confident that the image is compatible, you should declare "
            "compatibility in code using the `asCompatibleSubstituteFor` method. For example:\n"
            f'   myImage = DockerImageName.parse("{self.raw_name}").as_compatible_substitute_for_str("{ex}");\n'
            "and then use `myImage` instead."
        )


@dataclass(frozen=True)
class _GuavaHostAndPort:
    """AI code"""

    host: str
    port: int | None = None

    @classmethod
    def parse(cls, value: str) -> _GuavaHostAndPort:
        if value.startswith("["):
            end = value.find("]")
            if end < 0:
                raise ValueError(f"Invalid bracketed host: {value!r}")

            host = value[1:end]
            rest = value[end + 1 :]

            if not rest:
                return cls(host)

            if not rest.startswith(":"):
                raise ValueError(f"Invalid host/port: {value!r}")

            port_string = rest[1:]
        elif value.count(":") == 1:
            host, port_string = value.split(":", 1)
        else:
            # hostname with no port, or bare IPv6 literal
            return cls(value)

        if not port_string.isascii() or not port_string.isdigit():
            raise ValueError(f"Invalid port: {value!r}")

        port = int(port_string)
        if not 0 <= port <= 65535:
            raise ValueError(f"Port out of range: {value!r}")

        return cls(host, port)
