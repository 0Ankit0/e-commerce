from typing import Protocol

from pydantic import BaseModel

from ...models import User


class UserDataExportable(Protocol):
    export_key: str
    schema_class: type[BaseModel]

    @classmethod
    def export(cls, user: User) -> str | list[str]:
        ...


class UserFilesExportable(Protocol):
    @classmethod
    def export(cls, user: User) -> list[str]:
        ...
