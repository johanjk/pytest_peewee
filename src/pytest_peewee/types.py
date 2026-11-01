from abc import abstractmethod

import peewee as pw

from .isolation import RollbackDatabase

__all__ = ["DebugContext", "DebugHelper", "DebugQuery", "RollbackDatabase"]


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
