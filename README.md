# Pytest Peewee ORM extensions

[Pytest](https://github.com/pytest-dev/pytest/)
Extensions for the Python SQL ORM [Peewee](https://github.com/coleifer/peewee/).

## Features

* Minimal code to get up and running.
* All pw.Model and pw.Query is auto bound to the test database.
* Tables are created once, and all database operations are rolled back after each test.
* Failed queries are formatted, linted and shown in the failure report of the test.
* Any query can be easily printed using [rich](https://github.com/Textualize/rich) or linted with [sqlfluff](https://github.com/sqlfluff/sqlfluff).
* Statements that would break test isolation (`COMMIT`, DDL on MySQL) are refused with a clear error.
* Supports `postgres`, `sqlite` and `mysql`.

## Example

A complete test file `test_example.py`, with a query that fails:

```py
import peewee as pw
import pytest

class Table(pw.Model):
    field = pw.IntegerField()

@pytest.fixture(scope="module")
def database_models():
    yield [Table]

def test_wrong_join(database):
    a = Table.alias("t")

    q = Table.select().join(a.select(a.field), on=(Table.field == a.field))
    q.execute()
```

The failure report shows the failed query formatted and linted:

```bash
E       peewee.OperationalError: no such column: t.field
E       peewee query: SELECT "t1"."id", "t1"."field" FROM "table" AS "t1" INNER JOIN (SELECT "t"."field" FROM "table" AS "t") AS "t2" ON ("t"."field" = "t1"."field")

test_example.py:15: OperationalError
------------------------------ peewee query call -------------------------------
╭──────────────────────────────────────────────────────────────────────────────╮
│   1 SELECT                                                                   │
│   2     "t1"."id",                                                           │
│   3     "t1"."field"                                                         │
│   4 FROM "table" AS "t1"                                                     │
│   5 INNER JOIN                                                               │
│   6     (SELECT "t"."field" FROM "table" AS "t") AS "t2"                     │
│   7     ON ("t"."field" = "t1"."field")                                      │
│ Called from: test_example.py:15                                              │
│ L7:9-11 RF01: Reference '"t"."field"' refers to table/view not found in the  │
│ FROM clause or found in ancestor statement.                                  │
│                                                                              │
│ OperationalError: no such column: t.field                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
Query file: test-results/run-1/test_example.py-test_wrong_join/query.sql
Traceback hides library frames; show them with -o peewee_traceback=full
```

The query is also written to the linked `.sql` file, to copy or open in an editor.
Failure artifacts go to `test-results/run-<N>/<test id>/` in the rootdir (set with the `peewee_output` ini option).
Each run gets its own numbered folder; the last 3 runs are kept. The folder ignores itself in git.
With colors, the report shows `query.sql` as a link to the file; without (`--color=no`), the path to it.
Without colors, lint errors start with their line and columns in the query (`L7:9-11`), as the error is not highlighted.

The file holds the query, with the caller, lint errors (by line and columns) and query error as comments:

```sql
SELECT
    "t1"."id",
    "t1"."field"
FROM "table" AS "t1"
INNER JOIN
    (SELECT "t"."field" FROM "table" AS "t") AS "t2"
    ON ("t"."field" = "t1"."field")

-- Called from: /path/to/project/test_example.py:15
-- L7:9-11 RF01: Reference '"t"."field"' refers to table/view not found in the FROM clause or found in ancestor statement.
-- OperationalError: no such column: t.field
```

## Getting started

List the models whose tables the tests need:

```python
import peewee as pw
import pytest

class Table(pw.Model):
    field = pw.IntegerField()

@pytest.fixture(scope="module")
def database_models():
    yield [Table]
```

The tables are created once (before any test transaction), and dropped afterwards.

Create your tests by including the `database` fixture:

```python
def test_table_insert(database):
    Table.insert(field=1).execute()
    assert Table.select(Table.field).where(Table.field == 1).count() == 1
```

Or one of the following fixtures, (`sqlite`, `postgres`, `mysql`, `cockroach`) if test should be skipped while testing other database drivers.

Every test runs in a savepoint inside a module wide transaction, so data shared by the tests of a module can be added by overriding `module_database`:

```python
@pytest.fixture(scope="module")
def module_database(module_database):
    Table.create(field=42)
    yield module_database

def test_shared_data(database):
    assert Table.select().where(Table.field == 42).count() == 1
```

### Usage

Debug your queries by doing print/lint:

```python
def test_table_debug(database):
    q = Table.select(Table.field).order_by(Table.id)
    q.print()  # Simple formatted print
    # or
    assert q.lint()  # Also print linting errors from sqlfluff
```

`.lint()` can also be asserted (returns `True` on no linting errors.)

Expected errors are kept as they are, and cost nothing extra:

```python
def test_wrong_join(database):
    a = Table.alias("t")

    q = Table.select().join(a.select(a.field), on=(Table.field == a.field))
    with pytest.raises((pw.ProgrammingError, pw.OperationalError)):
        q.execute()
```

If the same query fails unexpectedly, the failure report shows it formatted and linted, as in the [example](#example).

#### Typing and the helpers

The helpers are added at runtime, so type checkers do not know them. Cast to `DebugHelper` if you care:

```python
from typing import cast

from pytest_peewee import DebugHelper


def test_table_debug_typed(database):
    q = Table.select(Table.field)
    assert cast(DebugHelper, q).lint()
```

### Test isolation

* `database.commit()` inside a test would commit the isolation transaction, and raises `IsolationError`.
* MySQL/MariaDB implicitly commit on DDL (`CREATE TABLE`, `ALTER`, `DROP`, `TRUNCATE`, ...), which would end the
  test transaction. Such statements raise `IsolationError` inside tests. Create tables via `database_models`, or use
  `Model.create_table(temporary=True)` for tables only one test needs (temporary tables do not commit).
* Binding a model during a test (`Model.bind(other_db)`) holds for that test only.

Configure with ini options:

```toml
[tool.pytest]
peewee_isolation = "strict"  # strict (error), warn (skip COMMIT / allow DDL with a warning) or off
peewee_scope = "module"      # scope of the connection and schema: session, package or module
peewee_unavailable = "xfail" # database unavailable or misconfigured: xfail, skip or fail
peewee_report = "framed"     # failed queries, .print() and .lint(): framed, or plain (no panel or line numbers)
peewee_output = "test-results" # failure artifacts (failed queries as .sql files), relative to the rootdir
peewee_traceback = "short"   # tracebacks of failed queries: short (without peewee and driver frames) or full
```

Use `peewee_report = "plain"` (or `-o peewee_report=plain`) to copy queries from the terminal;
formatting and colors are kept.

Tracebacks of failed queries end at the line running the query; peewee's and the driver's frames are left out.
Use `peewee_traceback = "full"` or `--fulltrace` to show them.

An unavailable database is an expected failure by default; run with `--runxfail` (e.g. in CI) to make it an error.

With `peewee_scope = "session"`, the connection and schema are set up once for the whole test run.
Connection and schema fixtures you override must then use the same scope: `@pytest.fixture(scope=pytest_peewee.scope)`.

### Configure alternate databases

By default, the `database` is in-memory sqlite. Other databases can be configured.

Most simply by setting the following environment variables:

```bash
export DBDRIVER="psycopg3"
export DBHOST="localhost"
export DBPORT="5432"
export DBDATABASE="test_db"
export DBUSER="dbuser"
export DBPASSWORD="secret"
pytest
```

`DBDRIVER` Should be one of Peewee's [supported schemas](https://docs.peewee-orm.com/en/latest/peewee/playhouse.html#connect).

[Database configuration](/docs/connection.md) can be done in a number of other ways, dependent on your needs.

* [setting](/docs/connection.md#default-configuration) default connection kwargs
* [setting](/docs/connection.md#env-var-configuration) env vars
* [setting](/docs/connection.md#connection-configuration) connection kwargs
* [setting](/docs/connection.md#database-string) database string
* [creating](/docs/connection.md#database-instance) `pw.Database` instance

### Multiple databases

Map each production database to a test database; anything unmapped goes to `database`.
A `DatabaseProxy` can be mapped itself, or by the database it is initialized with.
`database_from_env` makes test databases configured like `database`, from env vars with a prefix
(`ANALYTICS_DBDRIVER`, `ANALYTICS_DBHOST`, ...), and a separate in-memory sqlite database without them:

```python
analytics_db = pw.SqliteDatabase(None)

@pytest.fixture(scope="module")
def database_redirect(database_from_env):
    yield {analytics_db: database_from_env("ANALYTICS_")}
```

The test databases are rolled back like `database`: a module transaction, and a savepoint per test.

#### Databases the app creates

The redirect changes which database models and queries use, not database objects the app itself creates and uses:
`db.atomic()`, `db.execute_sql(...)`, `query.execute(db)` and binds made during a test still go to the real `db`.
Create them in one function of the app, and have the tests return `database` from it:

```python
def make_database(dbkwargs: dict[str, str]) -> pw.Database:
    """App code: the one place the app creates its database."""
    return pw.PostgresqlDatabase(**dbkwargs)

@pytest.fixture
def app_database(database, monkeypatch):
    # In a project, the import path of the function, e.g. "myapp.db.make_database".
    monkeypatch.setattr(f"{__name__}.make_database", lambda dbkwargs: database)
    yield database

def test_app_database(app_database):
    db = make_database({"database": "prod"})
    with db.atomic():
        Table.create(field=7)
    assert Table.select().where(Table.field == 7).count() == 1
```

## Install

The library is not on `pypi`, install directly from git.

### `requirements.txt` example

```bash
pytest-peewee @ git+ssh://git@github.com/johanjk/pytest-peewee
```

### uv example

```toml
dependencies = [
  "pytest-peewee",
]

[tool.uv.sources]
pytest-peewee = { git = "git+ssh://git@github.com/johanjk/pytest-peewee.git" }
```
