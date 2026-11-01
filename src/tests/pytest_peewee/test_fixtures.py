import peewee as pw
import pytest


def test_fixtures(database_string, setup_database, module_database, database):
    """Fixtures exists, and the test database is the module database."""
    assert database is module_database


def has_helper(exp: bool) -> pw.Query:
    """Lookup hooks on a simple query."""
    q = pw.Select(columns=[pw.Value(1)])
    assert hasattr(q, "print") == exp
    assert hasattr(q, "lint") == exp
    return q


def test_helpers_need_database():
    """Print/lint are installed for the session, but need a database."""
    q = has_helper(True)
    with pytest.raises(pw.InterfaceError):
        q.print()


def test_helpers(database):
    """Print/lint use the test database."""
    q = has_helper(True)
    q.print()
    assert q.lint()


def test_postgres_not_cockroach(run_testpath):
    """'postgres' skips Cockroach, though peewee's CockroachDatabase subclasses PostgresqlDatabase."""
    run_testpath("fixtures/postgres_cockroach.py").assert_outcomes(passed=2, skipped=2)


def test_mysql_password_param(mysql):
    """Temporary workaround: playhouse.db_url (peewee 4.5.3) passes PyMySQL's deprecated 'passwd'."""
    assert "passwd" not in mysql.connect_params
    assert "password" in mysql.connect_params


def test_envvar_templates_kept(database_default_envvar, database_kwargs):
    """Resolving env vars for 'database_kwargs' leaves the 'database_default_envvar' fixture value as it is."""
    assert database_default_envvar["dbtype"] == "$DBDRIVER"
