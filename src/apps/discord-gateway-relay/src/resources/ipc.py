from abc import ABC, abstractmethod
from typing import Optional
import json
import logging

from resources.secrets import CLUSTER_ID, RELEASE  # type: ignore[attr-defined]

logger = logging.getLogger("IPC")


class RelayPath(list):
    SEPARATOR = ":"

    def __init__(self, paths: str | list[str]):
        super().__init__(RelayPath.parse_segments(paths) if isinstance(paths, str) else paths)

        if len(self) < 1:
            raise ValueError("Given path cannot have zero segments!")

    def __str__(self):
        return RelayPath.SEPARATOR.join(self).upper()

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, str):
            return str(self) == __o
        elif isinstance(__o, list):
            return super().__eq__(__o)
        else:
            return False

    def segment_equals(self, index: int, value: str):
        """Returns if the chosen segment equals the given value."""
        try:
            return self[index] == value
        except IndexError:
            return False

    @staticmethod
    def parse_segments(path: str) -> list[str]:
        if isinstance(path, str):
            return path.split(RelayPath.SEPARATOR)
        else:
            raise TypeError("Provided parameter: path must be typeof string!")


class RelayRequest:
    def __init__(self, received_at: int, nonce: Optional[str], payload: dict):
        self.nonce = nonce
        self.payload = payload
        self.received_at = received_at

    async def respond(self, data: dict | list, *, channel: Optional[str] = None):
        pass


class RelayEndpoint(ABC):
    def __init__(self, path: str | RelayPath):
        self.path = path if isinstance(path, RelayPath) else RelayPath(path)

    @abstractmethod
    async def handle(self, request: RelayRequest):
        raise NotImplementedError(f"Endpoint {self.__class__.__name__} is not implemented.")


RELAY_ENDPOINTS: list[RelayEndpoint] = []
