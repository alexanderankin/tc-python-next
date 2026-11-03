import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


class Versioning(ABC):
    ANY: ClassVar[Versioning]

    valid: bool
    separator: str

    @abstractmethod
    def __str__(self) -> str:
        pass


class AnyVersion(Versioning):
    valid: bool = True
    separator: str = ":"

    def __str__(self) -> str:
        return "latest"


@dataclass(frozen=True)
class TagVersioning(Versioning):
    TAG_REGEX: ClassVar[str] = r"[\w][\w.\-]{0,127}"
    LATEST: ClassVar[TagVersioning]

    tag: str
    separator: str = ":"

    @property
    def valid(self) -> bool:
        return re.fullmatch(self.TAG_REGEX, self.tag) is not None

    def __str__(self) -> str:
        return self.tag


@dataclass(frozen=True)
class Sha256Versioning(Versioning):
    HASH_REGEX: ClassVar[str] = r"[0-9a-fA-F]{32,}"

    hash: str
    tag: str | None = None
    separator: str = "@"

    @property
    def valid(self) -> bool:
        if self.tag is not None and not re.fullmatch(TagVersioning.TAG_REGEX, self.tag):
            return False

        return re.fullmatch(self.HASH_REGEX, self.hash) is not None

    def __str__(self) -> str:
        return f"sha256:{self.hash}"


Versioning.ANY = AnyVersion()
TagVersioning.LATEST = TagVersioning("latest")
