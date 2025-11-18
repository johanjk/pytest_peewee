# Pytest Peewee ORM extensions

[Pytest](https://github.com/pytest-dev/pytest/)
Extensions to the Python SQL ORM [Peewee](https://github.com/coleifer/peewee/).

## Features

* Minimal code to get up and running.
* All pw.Model and pw.Query is auto bound to the test database.
* All database operations are transaction isolated and rolled back after each test.
* Failed queries prints formatted SQL in exception trace.
* Failed queries are linted and warning is output on linting problem.
* Any query can be easily printed using [rich](https://github.com/Textualize/rich) or linted with [sqlfluff](https://github.com/sqlfluff/sqlfluff).
* Supports `postgres`, `sqlite` and `mysql`.

## Getting started

To initialize tables, override the `database` fixture as follows:

```python
import peewee as pw
import pytest

class Table(pw.Model):
    field = pw.IntegerField()

@pytest.fixture
def database(database):
    Table.create_table()
    yield database
    if database.is_connection_usable():
        Table.drop_table()  # remember to drop tables, if using mysql
```

Create your tests by including the `database` fixture:

```python
def test_table_insert(database):
    Table.insert(field='data').execute()
    assert Table.select(Table.field).where(Table.field == 'data').count() == 1
```

### Usage

Debug your queries by doing print/lint:

```python
def test_table_insert(database):
    q = Table.select(Table.field).order_by(Table.id)
    q.print()  # Simple formatted print
    # or
    q.lint()  # Also print linting errors from sqlfluff
```

Failed queries are printed and linted:

```python
def test_wrong_join(database):
    a = Table.alias("t")

    q = Table.select().join(a.select(a.field), on=(Table.field == a.field))
    with pytest.raises((pw.ProgrammingError, pw.OperationalError)):
        q.execute()
```

Example output:

```bash
query_error.py:27: ProgrammingError
----------------------------- Captured stdout call -----------------------------
╭──────────────────────────────────────────────────────────────────────────────╮
│   1 WITH t2 AS (SELECT "t"."field" FROM "table" AS "t")                      │
│   2                                                                          │
│   3 SELECT                                                                   │
│   4     "t1"."id",                                                           │
│   5     "t1"."field"                                                         │
│   6 FROM "table" AS "t1"                                                     │
│   7 INNER JOIN t2 ON ("t"."field" = "t1"."field")                            │
│ RF01: Reference '"t"."field"' refers to table/view not found in the FROM     │
│ clause or found in ancestor statement.                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

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

`DBDRIVER` Should be one Peewee's [supported schemas](https://docs.peewee-orm.com/en/latest/peewee/playhouse.html#connect).

[Database configuration](/docs/connection.md) can be done in a number of other ways, dependent on your needs.

* [setting](/docs/connection.md#default-configuration) default connection kwargs
* [setting](/docs/connection.md#env-var-configuration) env vars
* [setting](/docs/connection.md#connection-configuration) connection kwargs
* [setting](/docs/connection.md#database-string) database string
* [creating](/docs/connection.md#database-instance) `pw.Database` instance

## Install

The library is not on `pypi`, install directly from git.

### `requirements.txt` example

```bash
pytest-peewee @ git+ssh://git@github.com/johanjk/pytest-peewee
```
