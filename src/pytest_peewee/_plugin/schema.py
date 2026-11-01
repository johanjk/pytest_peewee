"""Schema fixtures, and the isolated test databases on top of them."""

from contextlib import ExitStack, contextmanager
from typing import TYPE_CHECKING, cast

import pytest

from .._isolation import POLICIES, IsolationPolicy, RollbackDatabase, isolate, under_test
from .hooks import REDIRECT, scope

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Iterator

    import peewee as pw

    from .._redirect import DatabaseMap


@pytest.fixture(scope=scope)
def database_redirect() -> Iterator[DatabaseMap]:
    """Databases to redirect to test databases, for multi-database projects.

    `{source_database: test_database}`; a `DatabaseProxy` matches by itself, or by the database it was
    initialized with. Anything unmapped (or unbound) goes to `database`. The test databases are rolled
    back like `database`; `database_from_env` makes them configurable like it.
    """
    yield {}


@pytest.fixture(scope=scope)
def database_models() -> Iterator[list[type[pw.Model]]]:
    """Models whose tables are created once by `setup_schema`, and dropped after."""
    yield []


@pytest.fixture(scope=scope)
def database_isolation(pytestconfig: pytest.Config) -> Iterator[IsolationPolicy]:
    """Policy for statements breaking test isolation, from the 'peewee_isolation' ini option."""
    value = cast(str, pytestconfig.getini("peewee_isolation"))
    if value not in POLICIES:
        msg = f"peewee_isolation must be one of {POLICIES}, got {value!r}"
        raise pytest.UsageError(msg)
    yield value


@pytest.fixture(scope=scope)
def setup_schema(
    setup_database: pw.Database,
    database_models: list[type[pw.Model]],
    database_redirect: DatabaseMap,
    pytestconfig: pytest.Config,
) -> Iterator[pw.Database]:
    """Creates the tables of `database_models`, outside of any test transaction.

    Override to run migrations instead.
    """
    active = pytestconfig.stash[REDIRECT].active
    with active(setup_database, database_redirect):
        setup_database.create_tables(database_models)
    yield setup_database
    if database_models and setup_database.is_connection_usable():
        with active(setup_database, database_redirect):
            setup_database.drop_tables(database_models)


def _mapped(mapping: DatabaseMap, main: pw.Database) -> list[pw.Database]:
    """Test databases of `mapping` besides `main`, each once."""
    return list({id(database): database for database in mapping.values() if database is not main}.values())


@contextmanager
def _isolated(databases: Iterable[pw.Database], policy: IsolationPolicy) -> Generator[None]:
    """Each of `databases` under test and isolated while active, as `database` is."""
    with ExitStack() as stack:
        for database in databases:
            if database.is_closed():  # under test, close/connect only toggle a flag
                stack.enter_context(database.connection_context())
            stack.enter_context(isolate(stack.enter_context(under_test(database)), policy))
        yield


@pytest.fixture(scope="module")
def module_database(
    setup_schema: pw.Database,
    database_redirect: DatabaseMap,
    database_isolation: IsolationPolicy,
    pytestconfig: pytest.Config,
) -> Iterator[RollbackDatabase]:
    """Module wide transaction, rolled back after the module. Each test runs in a savepoint.

    The mapped test databases of `database_redirect` get their own module transaction.
    Override to add data shared by all tests in a module.
    """
    with (
        pytestconfig.stash[REDIRECT].active(setup_schema, database_redirect, owner="module_database"),
        under_test(setup_schema) as database,
        isolate(database, database_isolation),
        _isolated(_mapped(database_redirect, setup_schema), database_isolation),
    ):
        yield database


@pytest.fixture(scope="function")
def database(
    module_database: RollbackDatabase,
    database_redirect: DatabaseMap,
    database_isolation: IsolationPolicy,
    pytestconfig: pytest.Config,
) -> Iterator[RollbackDatabase]:
    """Function level database, in a savepoint of the module transaction rolled back after the test.

    The mapped test databases of `database_redirect` get a savepoint too.
    Model binds made during the test are reverted after it.
    """
    with (
        pytestconfig.stash[REDIRECT].active(module_database, database_redirect),
        isolate(module_database, database_isolation),
        _isolated(_mapped(database_redirect, module_database), database_isolation),
    ):
        yield module_database
