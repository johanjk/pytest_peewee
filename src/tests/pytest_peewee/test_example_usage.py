import peewee as pw
import pytest


class SomeTable(pw.Model):
    x = pw.IntegerField()


def test_nada(database):
    """Database fixture can be used."""


def test_create_no_database():
    """No database wont work."""
    with pytest.raises(pw.ImproperlyConfigured):
        SomeTable.create_table()


def test_create(database):
    """Can create table, and is bound."""
    SomeTable.create_table()


def test_isolation(database):
    """No conflict with prev test."""
    SomeTable.create_table(safe=False)


def test_database(database):
    """Can insert and retrieve."""
    SomeTable.create_table()
    SomeTable.insert(x=2).execute(database)

    query = (
        SomeTable
        .select(pw.fn.count(SomeTable.x))
    )
    assert query.scalar(database) == 1


def test_without_bind(database):
    """Queries doesn't have to be bound."""
    SomeTable.create_table()
    SomeTable.insert(x=2).execute()
    SomeTable.insert(x=2).execute(database)

    query = (
        SomeTable
        .select(pw.fn.count(SomeTable.x))
    )
    assert query.scalar(database) == 2


def test_no_rebind(database):
    """Swapping away from the test database is ignored."""
    SomeTable._meta.database = 22
    assert SomeTable._meta.database is database


def test_database_recreate(database):
    """Sanity check that re-reaction will fail."""
    SomeTable.create_table()
    with pytest.raises((pw.OperationalError, pw.ProgrammingError)):
        SomeTable.create_table(safe=False)


def test_bad_query(database):
    """Malformed queries are pretty-printed."""
    q = SomeTable.select()
    query = q.select_from(q.c.value)  # q has no 'value' column and will fail

    with pytest.raises(pw.DatabaseError) as target:
        query.execute()

    txt = str(target.value)
    assert txt != str(query)
    assert len(txt.split("\n")) == 2
    exp = 'SELECT "t1"."value" FROM (SELECT "t2"."id" FROM "sometable" AS "t2") AS "t1"'
    assert exp in txt

    assert query.lint()


def test_query_without_bind(database):
    """Raw queries does not have to be bound"""
    q = pw.RawQuery("SELECT 1").tuples()
    assert list(q.execute()) == [(1,)]


def test_query_no_rebind(database):
    """Swapping away from the test database is ignored."""
    q = pw.RawQuery("SELECT 1").tuples()
    q.bind(22)
    assert list(q.execute()) == [(1,)]
    q._database = 22
    assert list(q.execute()) == [(1,)]


def test_close_open(database):
    """Swapping away from the test database is ignored."""
    assert not database.is_closed()

    database.close()
    assert database.is_closed()
    assert not database._state.closed

    database.connect()
    assert not database.is_closed()
    assert not database._state.closed

    database.close()
    assert database.is_closed()
    assert not database._state.closed
