from abc import ABC, abstractmethod
from typing import Optional, TypedDict
from bloxlink_lib import load_modules


RELAY_ENDPOINTS: list['RelayEndpoint'] = []



class Response(TypedDict):
    """A response from each node."""

    success: bool
    error: str | None


class RelayPath(list[str]):
    """A path for an endpoint."""

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

        if isinstance(__o, list):
            return super().__eq__(__o)

        return False

    def segment_equals(self, index: int, value: str) -> bool:
        """Returns if the chosen segment equals the given value."""

        try:
            return self[index] == value
        except IndexError:
            return False

    @staticmethod
    def parse_segments(path: str) -> list[str]:
        if isinstance(path, str):
            return path.split(RelayPath.SEPARATOR)

        raise TypeError("Provided parameter: path must be typeof string!")


class RelayRequest(ABC):
    """A request object for the relay system."""
    def __init__(self, received_at: int, nonce: Optional[str], payload: dict):
        self.nonce = nonce
        self.payload = payload
        self.received_at = received_at

    async def respond(self, data: dict | list, *, channel: Optional[str] = None):
        """Respond to the request."""

        raise NotImplementedError("Respond() is not implemented.")


class RelayEndpoint(ABC):
    def __init__(self, path: str | RelayPath):
        self.path = path if isinstance(path, RelayPath) else RelayPath(path)

    @abstractmethod
    async def handle(self, request: RelayRequest) -> Response:
        raise NotImplementedError(f"Endpoint {self.__class__.__name__} is not implemented.")


def discover_endpoints():
    """Discovers all endpoints in the endpoints directory."""

    discovered_endpoints: list[RelayEndpoint] = []
    endpoint_modules = load_modules("app/endpoints", starting_path="./relay-server/")

    for endpoint_module in endpoint_modules:
        for endpoint_class_name in filter(
            lambda n: n != "RelayEndpoint" and n.lower().endswith("endpoint"), dir(endpoint_module)
        ):
            endpoint_class = getattr(endpoint_module, endpoint_class_name)

            if not issubclass(endpoint_class, RelayEndpoint):
                continue

            discovered_endpoints.append(endpoint_class())

    RELAY_ENDPOINTS.extend(discovered_endpoints)
