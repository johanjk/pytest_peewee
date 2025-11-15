from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager
from typing import cast

import peewee as pw
import pytest

from . import console
from .types import DebugContext, DebugQuery


@pytest.fixture(scope="function")
def use_database(monkeypatch: pytest.MonkeyPatch) -> Callable[[pw.Database], AbstractContextManager[None]]:
    """Injects the testing database as the query level database by default."""

    @contextmanager
    def func(database: pw.Database):
        with monkeypatch.context() as m:
            p = property(lambda self: database)  # noqa: ARG005
            p = p.setter(lambda self, value: None)  # noqa: ARG005
            m.setattr(pw.Metadata, "database", p, raising=False)
            m.setattr(pw.BaseQuery, "_database", p, raising=False)

            yield

    return func


@pytest.fixture(scope="function")
def query_helpers(monkeypatch: pytest.MonkeyPatch) -> Callable[[pw.Database], AbstractContextManager[None]]:
    """Add print/lint query helpers."""

    @contextmanager
    def func(database: pw.Database):
        def lint(self: pw.Query) -> bool:
            return console.print_lint(self, database)
        def prnt(self: pw.Query, stacklevel: int | None = 1) -> None:
            console.print_query(self, database, stacklevel + 1 if stacklevel is not None else None)

        with monkeypatch.context() as m:
            mapping = [
                cast(DebugContext, pw.Context),
                cast(DebugContext, pw.Query),
            ]
            for clazz in mapping:
                m.setattr(clazz, "print", prnt, raising=False)
                m.setattr(clazz, "lint", lint, raising=False)
            yield

    return func
