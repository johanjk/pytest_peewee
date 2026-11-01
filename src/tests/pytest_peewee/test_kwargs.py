# ruff: file-ignore[S106, S108]
import pydantic
import pytest
from playhouse.db_url import parse, schemes  # type: ignore[reportMissingTypeStubs]

from pytest_peewee.kwargs import Database, HostSpec, UserSpec


def roundtrip(**kwargs: object) -> dict[str, object]:
    """Build the url, and parse it back the way 'setup_database' does."""
    defaults = {
        "dbtype": "postgresql",
        "conn": HostSpec(host="h", port=None),
        "database": "d",
        "cred": None,
    }
    return parse(str(Database(**defaults | kwargs)), unquote_password=True, unquote_user=True)  # type: ignore[reportArgumentType]


@pytest.mark.parametrize("dbtype", sorted(s for s in schemes if "sqlite" not in s))
def test_server_schemes(dbtype):
    """Every registered server scheme reads back host, port, credentials, database and params."""
    r = roundtrip(
        dbtype=dbtype,
        conn=HostSpec(host="db.local", port=5432),
        cred=UserSpec(user="bob", password="p@ss:/w"), params={"application_name": "x"},
    )
    # Temporary workaround: playhouse.db_url (peewee 4.5.3) passes PyMySQL's deprecated 'passwd'.
    assert r.pop("passwd" if dbtype == "mysql" else "password") == "p@ss:/w"
    assert r == {
        "database": "d",
        "user": "bob",
        "host": "db.local",
        "port": 5432,
        "application_name": "x",
    }


@pytest.mark.parametrize("database", [":memory:", "/tmp/x.db", "x.db", "dir/x 1%.db"])
def test_sqlite(database):
    """Sqlite paths are kept as is."""
    assert roundtrip(dbtype="sqlite", conn=None, database=database) == {"database": database}


@pytest.mark.parametrize("cred", [
    UserSpec(user="bob", password="a b"),
    UserSpec(user="bob", password="a+b%41"),
    UserSpec(user="me@corp", password="x"),
    UserSpec(user="bob", password=None),
])
def test_credentials(cred):
    """Credentials survive peewee's 'unquote' decoding."""
    r = roundtrip(cred=cred)
    assert (r["user"], r.get("password")) == (cred.user, cred.password)


@pytest.mark.parametrize(("conn", "expected"), [
    (HostSpec(host="::1", port=5432), {"host": "::1", "port": 5432}),
    (HostSpec(host=None, port=5432), {"port": 5432}),
    (HostSpec(host="h", port=None), {"host": "h"}),
])
def test_host(conn, expected):
    """IPv6 hosts are bracketed, host and port are each optional."""
    assert roundtrip(conn=conn) == {"database": "d"} | expected


@pytest.mark.parametrize("build", [
    lambda: UserSpec(user="", password="secret"),
    lambda: HostSpec(host=None, port=None),
    lambda: HostSpec(host="/var/run/postgresql", port=None),
    lambda: Database(dbtype="postgresql", conn=None, database="we?ird", cred=None),
    lambda: Database(dbtype="postgresql", conn=None, database="we#ird", cred=None),
])
def test_unrepresentable(build):
    """Inputs an url cannot carry are rejected, instead of silently connecting elsewhere."""
    with pytest.raises(pydantic.ValidationError):
        build()
