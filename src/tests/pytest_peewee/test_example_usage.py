import peewee as pw
import pytest

from .test_isolation import assert_not_rewrapped


class SomeTable(pw.Model):  # ruff: ignore[D101]
    x = pw.IntegerField()


@pytest.fixture(scope="module")
def database_models():
    """Tables created once for the module."""
    yield [SomeTable]


def test_create_no_database():
    """Tests not requesting a database get no redirect, so unbound models have no database."""
    with pytest.raises(pw.ImproperlyConfigured):
        SomeTable.create_table()


def test_create(database):
    """Table from 'database_models' exists, and is bound."""
    assert SomeTable.table_exists()


def test_database(database):
    """Can insert and retrieve."""
    SomeTable.insert(x=2).execute(database)

    query = (
        SomeTable
        .select(pw.fn.count(SomeTable.x))
    )
    assert query.scalar(database) == 1


def test_without_bind(database):
    """Queries doesn't have to be bound."""
    SomeTable.insert(x=2).execute()
    SomeTable.insert(x=2).execute(database)

    query = (
        SomeTable
        .select(pw.fn.count(SomeTable.x))
    )
    assert query.scalar(database) == 2


def test_rebind_is_respected(database):
    """Binding during a test is respected for that test."""
    other = pw.SqliteDatabase(":memory:")
    SomeTable.bind(other)
    assert SomeTable._meta.database is other


def test_rebind_is_reverted(run_testpath):
    """Binding from one test does not leak into the next."""
    run_testpath("example_usage/rebind.py").assert_outcomes(passed=2)


def test_bad_query(database):
    """A failing query keeps the driver error, with the query added as a note."""
    q = SomeTable.select()
    query = q.select_from(q.c.value)  # q has no 'value' column and will fail

    with pytest.raises(pw.DatabaseError) as target:
        query.execute()

    # Original driver error is kept, the query is added as a note.
    assert_not_rewrapped(target.value)
    exp = 'SELECT "t1"."value" FROM (SELECT "t2"."id", "t2"."x" FROM "sometable" AS "t2") AS "t1"'
    if isinstance(database, pw.MySQLDatabase):
        exp = exp.replace('"', '`')
    assert f"peewee query: {exp}" in target.value.__notes__


def test_query_without_bind(database):
    """Raw queries does not have to be bound."""
    q = pw.RawQuery("SELECT 1").tuples()
    assert list(q.execute()) == [(1,)]


def test_query_bound_elsewhere(database):
    """A query bound to another database still runs on the test database."""
    other = pw.SqliteDatabase(":memory:")  # has no 'sometable'
    SomeTable.create(x=1)
    assert SomeTable.select().bind(other).count() == 1
