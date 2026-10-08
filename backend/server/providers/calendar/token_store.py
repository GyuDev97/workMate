from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


class OAuthTokenStore(Protocol):
    def read(self) -> str | None: ...
    def write(self, value: str) -> None: ...
    def delete(self) -> None: ...


class FileTokenStore:
    """A replaceable local store; the file is private to the current user (0600)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> str | None:
        try:
            return self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def write(self, value: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(value, encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)
        os.chmod(self.path, 0o600)

    def delete(self) -> None:
        self.path.unlink(missing_ok=True)
