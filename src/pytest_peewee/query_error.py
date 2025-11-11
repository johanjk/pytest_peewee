import functools
from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager

import peewee as pw
import pytest

from . import fmt


def catch_execute_error(database: pw.Database):
    """Wrapper catching database execute errors and pretty prints them."""
    func = database.execute

    @functools.wraps(database.execute)
    def execute(query, *args, **kwargs):
        try:
            return func(query, *args, **kwargs)
        except pw.DatabaseError as err:
            query_str = fmt.render(query)
            ext = type(err)
            msg = f"Exception during query:\n{query_str}"
            query.lint()
            raise ext(msg) from err

    return execute


@pytest.fixture(scope="function")
def query_error(monkeypatch) -> Callable[[pw.Database], AbstractContextManager]:
    """Query pretty printed if failed during tests."""

    @contextmanager
    def func(database):
        with monkeypatch.context() as m:
            m.setattr(database, "execute", catch_execute_error(database))
            yield

    return func
