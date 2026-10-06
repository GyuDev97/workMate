from typing import Any, Protocol


class Tool(Protocol):
    name: str
    description: str

    def execute(self, **kwargs: Any) -> Any: ...
