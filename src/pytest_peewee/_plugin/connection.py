"""Connection fixtures: kwargs, from env vars or defaults, to a database string, to a usable database."""

from collections.abc import Iterator
from contextlib import ExitStack
from typing import TYPE_CHECKING

import peewee as pw
import playhouse.db_url as pwdb_url  # type: ignore[reportMissingTypeStubs]
import pydantic
import pytest

from .._kwargs import Database, HostSpec, UserSpec
from .._parse_env import parse_env
from .hooks import scope

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

type sdict = dict[str, str]  # ruff: ignore[PYI042]
type DatabaseFactory = Callable[[str], pw.Database]
"""`database_from_env`: makes a test database from env vars with the given prefix."""

_ENV_VARS = {
    "dbtype":   "DBDRIVER",
    "host":     "DBHOST",
    "port":     "DBPORT",
    "database": "DBDATABASE",
    "user":     "DBUSER",
    "password": "DBPASSWORD",
}
"""Connection kwargs and the env vars configuring them, see `database_default_envvar`."""

_MEMORY = {"dbtype": "sqlite", "database": ":memory:"}


def unavailable(config: pytest.Config, msg: str) -> None:
    """Apply the 'peewee_unavailable' policy; returns only for 'fail' (or 'xfail' with --runxfail).

    The caller raises after this, which makes the test error.
    """
    match config.getini("peewee_unavailable"):
        case "xfail":
            pytest.xfail(msg)  # no-op with --runxfail
        case "skip":
            pytest.skip(msg)
        case _:
            pass


@pytest.fixture(scope=scope)
def database_default_kwargs() -> Iterator[sdict]:
    """Defaults database connection kwargs when env vars are not set.

    Defaults to sqlite memory.
    """
    yield dict(_MEMORY)


@pytest.fixture(scope=scope)
def database_default_envvar() -> Iterator[sdict]:
    """Connection kwargs with env var support.

    Takes precedence over 'database_default_kwargs'.
    Values may reference environment variables as "$NAME" or "${NAME}"; unset ones are left to the defaults.
    """
    yield {
        "dbtype":   "$DBDRIVER",
        "host":     "$DBHOST",
        "port":     "$DBPORT",
        "database": "$DBDATABASE",
        "user":     "$DBUSER",
        "password": "$DBPASSWORD",
    }


@pytest.fixture(scope=scope)
def database_kwargs(database_default_envvar: sdict, database_default_kwargs: sdict) -> Iterator[sdict]:
    """Realizes env vars and merges env and defaults."""
    kwargs = parse_env(database_default_envvar)
    yield database_default_kwargs | {
        k: v for k, v in kwargs.items() if v
    }


def connection_params(kwargs: Mapping[str, str]) -> sdict:
    """Extra connection params for the database type of `kwargs`, naming the connecting program."""
    name = "pytest-peewee"
    match kwargs["dbtype"].split("+")[0]:
        case "mysql":
            return {"program_name": name}
        case "postgres" | "postgresql" | "postgresext" | "postgresqlext" | "psycopg3" | "cockroachdb" | "crdb":
            return {"application_name": name}
        case _:
            return {}


def build_database_string(kwargs: Mapping[str, str], params: Mapping[str, str], config: pytest.Config) -> str:
    """Validated peewee database string of connection `kwargs` and extra `params`.

    Applies the 'peewee_unavailable' policy to missing or invalid config.
    """
    if not kwargs:
        msg = "Could not connect; no config found."
        unavailable(config, msg)
        raise ValueError(msg)
    rest = dict(kwargs)
    host = rest.pop("host", None)
    port = rest.pop("port", None)
    user = rest.pop("user", None)
    password = rest.pop("password", None)
    try:
        conn = HostSpec(host=host, port=port) if host or port else None  # type: ignore[reportArgumentType]
        cred = UserSpec(user=user or "", password=password) if user or password else None
        return str(Database(conn=conn, cred=cred, database=rest.pop("database", None), params=dict(params), **rest))
    except pydantic.ValidationError as err:
        msg = f"Could not connect; Database '{kwargs}', {err.errors()}."
        unavailable(config, msg)
        raise


def connect(database_string: str, config: pytest.Config) -> pw.Database:
    """Database of `database_string`, checked to be usable.

    Applies the 'peewee_unavailable' policy to an unusable database.
    """
    try:
        database = pwdb_url.connect(
            database_string,
            unquote_password=True,
            unquote_user=True,
        )
    except (pw.DatabaseError, pw.OperationalError, RuntimeError) as err:
        msg = f"Could not connect; Database '{database_string}'."
        raise ValueError(msg) from err

    # Temporary workaround: playhouse.db_url (peewee 4.5.3) passes PyMySQL's deprecated 'passwd'.
    if isinstance(database, pw.MySQLDatabase) and "passwd" in database.connect_params:
        database.connect_params["password"] = database.connect_params.pop("passwd")

    try:
        with database.atomic():
            pass
    except pw.OperationalError as err:
        msg = f"Could not connect; Database '{database_string}'."
        unavailable(config, msg)
        raise ValueError(msg) from err

    assert isinstance(database, pw.Database)
    return database


@pytest.fixture(scope=scope)
def database_params(database_kwargs: sdict) -> Iterator[sdict]:
    """Extra database connection params appended as '?' params to Database constructor."""
    yield connection_params(database_kwargs)


@pytest.fixture(scope=scope)
def database_string(
    database_kwargs: sdict, database_params: sdict, pytestconfig: pytest.Config,
) -> Iterator[str]:
    """Builds the peewee database string.

    as defined in: http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#db-url

    Defaults to 'sqlite:///:memory:', unless 'database_default_kwargs' is overridden, or default env vars were set.
    Can be overridden to match your underlying database, but using env or defaults is preferable.
    """
    yield build_database_string(database_kwargs, database_params, pytestconfig)


@pytest.fixture(scope=scope)
def setup_database(database_string: str, pytestconfig: pytest.Config) -> Iterator[pw.Database]:
    """Realizes initial database object."""
    database = connect(database_string, pytestconfig)
    with database.connection_context():
        # sqlite memory must stay open to not clear itself
        yield database


@pytest.fixture(scope=scope)
def database_from_env(pytestconfig: pytest.Config) -> Iterator[DatabaseFactory]:
    """Factory of extra test databases, configured like `database` from env vars with a prefix.

    `database_from_env("ANALYTICS_")` reads `ANALYTICS_DBDRIVER`, `ANALYTICS_DBHOST`, ... ;
    without them it is a separate in-memory sqlite database. Use it in `database_redirect`.
    """
    with ExitStack() as stack:

        def make(prefix: str) -> pw.Database:
            env = parse_env({key: f"${{{prefix}{var}}}" for key, var in _ENV_VARS.items()})
            kwargs = _MEMORY | {key: value for key, value in env.items() if value}
            database = connect(build_database_string(kwargs, connection_params(kwargs), pytestconfig), pytestconfig)
            stack.enter_context(database.connection_context())  # sqlite memory must stay open
            return database

        yield make
