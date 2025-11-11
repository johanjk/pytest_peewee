from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager

import peewee as pw
import pytest

type Tr = pw._transaction | None  # type: ignore[reportPrivateUsage] # noqa: SLF001


@pytest.fixture(scope="function")
def transaction(monkeypatch: pytest.MonkeyPatch) -> Callable[[pw.Database], AbstractContextManager[Tr]]:
    """Per test isolation of all database operations."""

    @contextmanager
    def func(database: pw.Database) -> Iterator[Tr | None]:
        try:
            with database.atomic() as tr:
                _connect = database.connect

                def connect_mock(self=database, reuse_if_open=True):  # noqa: ARG001
                    self._mock_closed = False
                    return _connect(reuse_if_open=True)

                def is_closed_mock(self=database):
                    return self._mock_closed

                def close_mock(self=database):
                    self._mock_closed = True

                try:
                    with monkeypatch.context() as m:
                        m.setattr(database, "_mock_closed", False, raising=False)
                        m.setattr(database, "connect", connect_mock)
                        m.setattr(database, "close", close_mock)
                        m.setattr(database, "is_closed", is_closed_mock)
                        yield tr

                finally:
                    tr.rollback()

        except pw.DatabaseError:
            yield None

    return func
