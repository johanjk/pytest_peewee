import functools
from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager
from typing import Any

import peewee as pw
import pytest

from . import fmt
from .use_database import DebugQuery


def catch_execute_error(database: pw.Database) -> Callable[..., Any]:
    """Wrapper catching database execute errors and pretty prints them."""
    func = database.execute

    @functools.wraps(database.execute)
    def execute(query: DebugQuery, *args, **kwargs):  # type: ignore[reportMissingParameterType]
        __tracebackhide__ = True
        try:
            return func(query, *args, **kwargs)
        except (pw.DatabaseError, pw.ProgrammingError) as err:
            msg = f"{type(err).__name__}: {str(err)}"
            _ = query.lint(subtext=msg) and query.print(subtext=msg)
            query_str = fmt.render(query, database)
            ext = type(err)
            msg = f"Exception during query:\n{query_str}"
            raise ext(msg) from err

    return execute


@pytest.fixture(scope="function")
def query_error(monkeypatch: pytest.MonkeyPatch) -> Callable[[pw.Database], AbstractContextManager[None]]:
    """Query pretty printed if failed during tests."""
    __tracebackhide__ = True

    @contextmanager
    def func(database: pw.Database):
        __tracebackhide__ = True
        with monkeypatch.context() as m:
            m.setattr(database, "execute", catch_execute_error(database))
            yield

    return func
