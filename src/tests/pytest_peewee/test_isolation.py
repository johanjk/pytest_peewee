import peewee as pw
import pytest

from pytest_peewee import IsolationError, IsolationWarning, RollbackDatabase
from pytest_peewee.isolation import (
    FAILED_QUERY,
    MySQLRollbackDatabase,
    implicit_commit,
    isolate,
    under_test,
)


class Row(pw.Model):  # ruff: ignore[D101]
    x = pw.IntegerField(unique=True)


@pytest.fixture
def sqlite_db():
    """Standalone connected sqlite database with a 'row' table."""
    db = pw.SqliteDatabase(":memory:")
    with db.connection_context():
        Row.bind(db)
        db.create_tables([Row])
        yield db
    Row.bind(None)


def count(db: pw.Database) -> int:
    """Rows in 'row'."""
    return db.execute_sql("SELECT count(*) FROM row").fetchone()[0]


def assert_not_rewrapped(err: BaseException):
    """Peewee's own exception, wrapping the driver error."""
    assert err.__cause__ is None
    assert not isinstance(err.__context__, pw.PeeweeException)
    assert str(err) == str(err.__context__)


@pytest.mark.parametrize(("sql", "commits"), [
    ("CREATE TABLE t (x INT)", True),
    ("  create table if not exists t (x INT)", True),
    ("CREATE INDEX i ON t (x)", True),
    ("DROP TABLE t", True),
    ("ALTER TABLE t ADD y INT", True),
    ("TRUNCATE t", True),
    ("RENAME TABLE t TO u", True),
    ("LOCK TABLES t WRITE", True),
    ("START TRANSACTION", True),
    ("CREATE TEMPORARY TABLE t (x INT)", False),
    ("DROP TEMPORARY TABLE t", False),
    ("SELECT 1", False),
    ("INSERT INTO t VALUES (1)", False),
    ("SAVEPOINT s1", False),
    ("ROLLBACK TO SAVEPOINT s1", False),
    ("RELEASE SAVEPOINT s1", False),
])
def test_implicit_commit(sql, commits):
    """MySQL implicit commit detection."""
    assert implicit_commit(sql) is commits


def test_class_swap_restored(sqlite_db):
    """The original class is restored, with no state left behind."""
    with under_test(sqlite_db) as db:
        assert isinstance(db, RollbackDatabase)
        assert isinstance(db, pw.SqliteDatabase)
        with under_test(db):  # reentrant
            assert type(db).__name__ == "TestSqliteDatabase"
        assert isinstance(db, RollbackDatabase)
    assert type(sqlite_db) is pw.SqliteDatabase
    assert not any(k.startswith("_ppw") for k in vars(sqlite_db))


def test_mysql_class():
    """Only MySQL databases get the MySQL specific guards; needs no connection."""
    with under_test(pw.MySQLDatabase(None)) as db:
        assert isinstance(db, MySQLRollbackDatabase)
        assert isinstance(db, pw.MySQLDatabase)
    with under_test(pw.SqliteDatabase(None)) as db:
        assert isinstance(db, RollbackDatabase)
        assert not isinstance(db, MySQLRollbackDatabase)


def test_connect_close(sqlite_db):
    """Close/connect only toggle a flag, with peewee's semantics."""
    with under_test(sqlite_db) as db:
        assert db.connect(True) is False
        assert db.connect(reuse_if_open=True) is False
        with pytest.raises(pw.OperationalError, match="already opened"):
            db.connect()

        assert db.close() is True
        assert db.is_closed()
        assert db.close() is False
        assert count(db) == 0  # autoconnect reopens
        assert not db.is_closed()

        db.close()
        assert db.connect() is True
    assert not sqlite_db.is_closed()


def test_isolate_rolls_back(sqlite_db):
    """Everything inside is rolled back, nested levels use savepoints."""
    with under_test(sqlite_db) as db:
        with isolate(db):
            Row.create(x=1)
            with isolate(db):
                Row.create(x=2)
                assert count(db) == 2
            assert count(db) == 1
        assert count(db) == 0


def test_isolate_recovers_closed(sqlite_db):
    """A test closing the database does not break the rollback."""
    with under_test(sqlite_db) as db, isolate(db):
        Row.create(x=1)
        db.close()
    assert count(sqlite_db) == 0


def test_commit_strict(sqlite_db):
    """COMMIT inside an isolated test is refused."""
    with under_test(sqlite_db) as db, isolate(db, "strict"), pytest.raises(IsolationError, match="COMMIT"):
        db.commit()


def test_commit_warn(sqlite_db):
    """With 'warn' the COMMIT is skipped, so the rollback still holds."""
    with under_test(sqlite_db) as db:
        with isolate(db, "warn"):
            Row.create(x=1)
            with pytest.warns(IsolationWarning, match="COMMIT") as record:
                db.commit()
            assert record[0].filename == __file__  # the caller, not peewee or the plugin
        assert count(db) == 0


def test_commit_off(sqlite_db):
    """With 'off' the COMMIT goes through."""
    with under_test(sqlite_db) as db:
        with isolate(db, "off"):
            Row.create(x=1)
            db.commit()
            db.begin()  # keep the rollback valid
        assert count(db) == 1


def test_commit_outside_isolation(sqlite_db):
    """No guard without an isolation transaction."""
    with under_test(sqlite_db) as db, db.atomic():
        Row.create(x=1)
    assert count(sqlite_db) == 1


def test_failed_query_is_attached(sqlite_db):
    """The driver error is kept; the query is attached for the report."""
    with under_test(sqlite_db) as db:
        Row.create(x=1)
        query = Row.insert(x=1)
        with pytest.raises(pw.IntegrityError) as err:
            query.execute()

    assert_not_rewrapped(err.value)
    assert getattr(err.value, FAILED_QUERY) == (query, db)
    assert err.value.__notes__ == ['peewee query: INSERT INTO "row" ("x") VALUES (1)']


class Scratch(pw.Model):
    """No indexes: MySQL implicitly commits CREATE INDEX, even on a temporary table."""
    x = pw.IntegerField()


def test_mysql_ddl_guard(mysql):
    """DDL inside a MySQL test is refused before it commits."""
    with pytest.raises(IsolationError, match="MySQL implicitly commits"):
        Scratch.create_table()
    assert not Scratch.table_exists()

    with pytest.raises(IsolationError, match="MySQL implicitly commits"):
        mysql.execute_sql("CREATE TABLE guard_test (x INT)")
    assert not mysql.table_exists("guard_test")


def test_mysql_temporary_table(mysql):
    """Temporary tables do not commit, and are allowed."""
    Scratch.create_table(temporary=True)
    mysql.execute_sql("CREATE TEMPORARY TABLE guard_tmp (x INT)")
