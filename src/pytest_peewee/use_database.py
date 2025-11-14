from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager

import peewee as pw
import pytest

from . import console


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
def query_helpers(monkeypatch) -> Callable[[pw.Database], AbstractContextManager]:
    """Add print/lint query helpers."""

    @contextmanager
    def func(database):
        lint = lambda x: console.print_lint(x, database)
        prnt = lambda x, stacklevel=1: console.print_query(x, database, stacklevel + 1 if stacklevel is not None else None)
        with monkeypatch.context() as m:
            for clazz in (pw.Context, pw.Query):
                m.setattr(clazz, "print", prnt, raising=False)
                m.setattr(clazz, "lint", lint, raising=False)
            yield

    return func
