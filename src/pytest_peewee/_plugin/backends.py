"""`database`, skipping the test unless it is of a given backend."""

from collections.abc import Iterator

import peewee as pw
import playhouse.cockroachdb as pwc  # type: ignore[reportMissingTypeStubs]
import pytest

from .._isolation import RollbackDatabase


@pytest.fixture(scope="function")
def sqlite(database: RollbackDatabase) -> Iterator[RollbackDatabase]:
    """Sqlite database."""
    if not isinstance(database, pw.SqliteDatabase):
        pytest.skip("Not an sqlite database.")
        return

    yield database


@pytest.fixture(scope="function")
def postgres(database: RollbackDatabase) -> Iterator[RollbackDatabase]:
    """Postgres database; not Cockroach, though peewee's `CockroachDatabase` subclasses `PostgresqlDatabase`."""
    if isinstance(database, pwc.CockroachDatabase):
        pytest.skip("Not a postgres database, but Cockroach.")
        return
    if not isinstance(database, pw.PostgresqlDatabase):
        pytest.skip("Not a postgres database.")
        return

    yield database


@pytest.fixture(scope="function")
def mysql(database: RollbackDatabase) -> Iterator[RollbackDatabase]:
    """MySQL database."""
    if not isinstance(database, pw.MySQLDatabase):
        pytest.skip("Not a MySQL database.")
        return

    yield database


@pytest.fixture(scope="function")
def cockroach(database: RollbackDatabase) -> Iterator[RollbackDatabase]:
    """Cockroachdb database."""
    if not isinstance(database, pwc.CockroachDatabase):
        pytest.skip("Not a Cockroach database.")
        return

    yield database
