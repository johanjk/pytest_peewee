from abc import abstractmethod
from collections.abc import Callable
from contextlib import AbstractContextManager

import peewee as pw

type DatabaseCtx = Callable[[pw.Database], AbstractContextManager[None]]

type Tr = pw._transaction  # type: ignore[reportPrivateUsage] # noqa: SLF001


class RollbackDatabase(pw.Database):
    """Transaction rollback patched database."""
    _mock_closed: bool = False


class DebugHelper:
    """Debuggable query like type."""
    @abstractmethod
    def print(self, subtext: str | None = None) -> None:
        """Pretty print a formatted and syntax highlighted SQL of this."""
    @abstractmethod
    def lint(self, subtext: str | None = None) -> bool:
        """Pretty linting of this query.

        Returns:
            True if linting found no problems.
        """


class DebugQuery(DebugHelper, pw.Query):
    """Query patched with debug helpers."""


class DebugContext(DebugHelper, pw.Context):
    """Context patched with debug helpers."""
