from typing import TypedDict, NotRequired


class Response(TypedDict):
    success: bool
    error: NotRequired[str]
