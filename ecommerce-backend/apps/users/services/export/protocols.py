from typing import Any, Protocol

from ...models import User


class UserDataExportable(Protocol):
    export_key: str
    schema_class: Any

    @classmethod
    def export(cls, user: User) -> str | list[str]:
        ...


class UserFilesExportable(Protocol):
    @classmethod
    def export(cls, user: User) -> list[str]:
        ...
