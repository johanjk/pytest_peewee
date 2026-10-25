from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from typing import Literal, cast

import peewee as pw
import pytest

from .types import RollbackDatabase, Tr


@pytest.fixture(scope="function")
def transaction(monkeypatch: pytest.MonkeyPatch) -> Callable[[pw.Database], AbstractContextManager[Tr | None]]:
    """Per test isolation of all database operations."""

    @contextmanager
    def func(database: pw.Database) -> Generator[Tr | None]:
        try:
            with database.atomic() as tr:
                tr = cast(Tr, tr)

                _connect = database.connect
                database = cast(RollbackDatabase, database)

                def connect_mock(self: RollbackDatabase = database, reuse_if_open: bool = True) -> bool:  # noqa: ARG001
                    self._mock_closed = False  # type: ignore[reportPrivateUsage]
                    return _connect(reuse_if_open=True)

                def is_closed_mock(self: RollbackDatabase = database) -> bool:
                    return self._mock_closed  # type: ignore[reportPrivateUsage]

                def close_mock(self: RollbackDatabase = database) -> Literal[False]:
                    self._mock_closed = True  # type: ignore[reportPrivateUsage]
                    return False

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
