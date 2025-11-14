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

## Getting started

[Database configuration](/docs/connection.md) can be done in a number of ways, dependent on your needs.

* [setting](/docs/connection.md#default-configuration) default connection kwargs
* [setting](/docs/connection.md#env-var-configuration) env vars
* [setting](/docs/connection.md#connection-configuration) connection kwargs
* [setting](/docs/connection.md#database-string) database string
* [creating](/docs/connection.md#database-instance) `pw.Database` instance

## Usage

To initialize tables, override `database` as follows:

```python
import peewee as pw
import pytest

class Table(pw.Model):
    field = pw.IntegerField()

@pytest.fixture
def database(database):
    Table.create_table()
    yield database
    # drop tables here, if using mysql
    Table.drop_table()
```

Create your tests by including the `database` fixture:

```python
def test_table_insert(database):
    Table.insert(field='data').execute()
    assert Table.select(Table.field).where(Table.field == 'data').count() == 1
```

Debug your queries by doing print/lint:

```python
def test_table_insert(database):
    q = Table.select(Table.field).order_by(Table.id)
    q.print()  # Simple formatted print
    # or
    q.lint()  # Also print linting errors from sqlfluff
```

## Install

The library is not on pypi, install directly from git.

### `requirements.txt` example

```bash
pytest-peewee @ git+ssh://git@github.com/johanjk/pytest-peewee
```
