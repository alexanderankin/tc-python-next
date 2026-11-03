from abc import ABC, abstractmethod

from types import TracebackType
from typing import Hashable


class Startable(ABC, Hashable):
    def __init__(self):
        self.dependencies: set[Startable] = set()

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()
