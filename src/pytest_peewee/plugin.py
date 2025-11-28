from collections.abc import Iterator
from contextlib import AbstractContextManager
from typing import cast

import peewee as pw
import playhouse.cockroachdb as pwc  # type: ignore[reportMissingTypeStubs]
import playhouse.db_url as pwdb_url  # type: ignore[reportMissingTypeStubs]
import pydantic
import pytest

from .kwargs import Database, HostSpecBlock, UserSpec
from .parse_env import parse_env
from .transaction import RollbackDatabase
from .types import DatabaseCtx

type sdict = dict[str, str]  # noqa: PYI042


@pytest.fixture(scope="module")
def database_default_kwargs() -> Iterator[sdict]:
    """Defaults database connection kwargs when env vars are not set.

    Defaults to sqlite memory.
    """
    yield {
        "dbtype":   "sqlite",
        "database": ":memory:",
    }


@pytest.fixture(scope="module")
def database_default_envvar() -> Iterator[sdict]:
    """Connection kwargs with env var support.

    Takes precedence over 'database_default_kwargs'.
    Is allowed to be loaded from environment variables. the syntax is "$ENV_VAR_NAME".
    """
    yield {
        "dbtype":   "$DBDRIVER",
        "host":     "$DBHOST",
        "port":     "$DBPORT",
        "database": "$DBDATABASE",
        "user":     "$DBUSER",
        "password": "$DBPASSWORD",
    }


@pytest.fixture(scope="module")
def database_kwargs(database_default_envvar: sdict, database_default_kwargs: sdict) -> Iterator[sdict]:
    """Realizes env vars and merges env and defaults."""
    kwargs = parse_env(database_default_envvar)  # type: ignore[reportArgumentType]
    yield database_default_kwargs | {
        k: v for k, v in kwargs.items() if v
    }


@pytest.fixture(scope="module")
def database_params(database_kwargs: sdict) -> Iterator[sdict]:
    """Extra database connection params appended as '?' params to Database constructor."""
    name = "pytest-peewee"
    match database_kwargs["dbtype"].split('+')[0]:
        case "mysql":
            yield {"program_name": name}
        case "postgres" | "postgresql" | "psycopg3":
            yield {"application_name": name}
        case _:
            yield {}


@pytest.fixture(scope="module")
def database_string(database_kwargs: sdict, database_params: sdict) -> Iterator[str]:
    """Builds the peewee database string.

    as defined in: http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#db-url

    Defaults to 'sqlite:///:memory:', unless 'database_default_kwargs' is overridden, or default env vars were set.
    Can be overridden to match your underlying database, but using env or defaults is preferable.
    """
    if not database_kwargs:
        msg = "Could not connect; no config found."
        pytest.xfail(msg)
        raise ValueError(msg)
    try:
        conn = None
        cred = None
        if database_kwargs["database"] != ":memory:":
            conn = HostSpecBlock(host=database_kwargs.pop("host", ""), port=database_kwargs.pop("port", None))
            cred = UserSpec(user=database_kwargs.pop("user", ""), password=database_kwargs.pop("password", None))

        yield str(Database(conn=[conn] if conn else None, cred=cred,
                           params=database_params, **database_kwargs))
    except pydantic.ValidationError as err:
        msg = f"Could not connect; Database '{database_kwargs}', {err.errors()}."
        pytest.xfail(msg)
        raise


@pytest.fixture(scope="module")
def setup_database(database_string: str) -> Iterator[pw.Database]:
    """Realizes initial database object."""
    try:
        database = pwdb_url.connect(
            database_string,
            unquote_password=True,
        )
    except (pw.DatabaseError, pw.OperationalError, RuntimeError) as err:
        msg = f"Could not connect; Database '{database_string}'."
        raise ValueError(msg) from err

    try:
        with database.atomic():
            pass
    except pw.OperationalError as err:
        msg = f"Could not connect; Database '{database_string}'."
        pytest.xfail(msg)
        raise ValueError(msg) from err

    assert isinstance(database, pw.Database)

    with database.connection_context():
        # sqlite memory must stay open to not clear itself
        yield database


@pytest.fixture(scope="function")
def pre_hook_database(setup_database: pw.Database) -> Iterator[pw.Database]:
    """Database before hooks are active.

    Use with caution, as rollback helpers and database auto-selector is not yet active.
    """
    yield setup_database


@pytest.fixture(scope="function")
def post_hook_database(
    pre_hook_database: pw.Database,
    use_database: DatabaseCtx,
    query_helpers: DatabaseCtx,
    query_error: DatabaseCtx,
) -> Iterator[pw.Database]:
    """Adds database auto-selector and query helpers."""
    with (
        use_database(pre_hook_database),
        query_helpers(pre_hook_database),
        query_error(pre_hook_database),
    ):
        yield pre_hook_database


@pytest.fixture(scope="function")
def pre_transaction_database(post_hook_database: pw.Database) -> Iterator[pw.Database]:
    """Database before rollback helper is active.

    Use with caution, as rollback helpers is not yet active.
    """
    yield post_hook_database


@pytest.fixture(scope="function")
def post_transaction_database(pre_transaction_database: pw.Database, transaction: DatabaseCtx) -> Iterator[RollbackDatabase]:
    """Open database with active auto-rollback transaction."""
    with transaction(pre_transaction_database):
        yield cast(RollbackDatabase, pre_transaction_database)


@pytest.fixture(scope="function")
def database(post_transaction_database: RollbackDatabase) -> Iterator[RollbackDatabase]:
    """Function level database."""
    yield post_transaction_database


@pytest.fixture(scope="function")
def sqlite(database: RollbackDatabase) -> Iterator[RollbackDatabase]:
    """Sqlite database."""
    if not isinstance(database, pw.SqliteDatabase):
        pytest.skip("Not an sqlite database.")
        return

    yield database


@pytest.fixture(scope="function")
def postgres(database: RollbackDatabase) -> Iterator[RollbackDatabase]:
    """Postgres database."""
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
