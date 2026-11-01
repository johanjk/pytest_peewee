# Configure database connection

The database can be configured in a number of ways. The [env-var](#env-var-configuration) method is recommended.

The examples below use `scope="module"`, the default of the `peewee_scope` ini option.
If you change `peewee_scope`, override with `@pytest.fixture(scope=pytest_peewee.scope)` instead.

## Default configuration

Set a default configuration that matches your specific development environment.
Note that env vars will replace defaults, if present.

```python
import pytest

@pytest.fixture(scope="module")
def database_default_kwargs():
    yield {
        'dbtype': 'psycopg3',
        'host': '127.0.0.1',
        'port': '5432',
        'database': 'test_db',
        'user': 'dbuser',
        'password': 'secret',
    }
```

## Env var configuration

In the simplest of cases, set the following env vars to match your configuration before running tests:

```bash
export DBDRIVER="psycopg3"
export DBHOST="localhost"
export DBPORT="5432"
export DBDATABASE="test_db"
export DBUSER="dbuser"
export DBPASSWORD="secret"
pytest
```

If additional `env` keys are wanted, override the following:

```python
@pytest.fixture(scope="module")
def database_default_envvar():
    yield {
        'dbtype':   '$DBDRIVER',
        'host':     '$DBHOST',
        'port':     '$DBPORT',
        'database': '$DBDATABASE',
        'user':     '$DBUSER',
        'password': '$DBPASSWORD',
    }
```

### Using hatch `hatch.toml`

```toml
[envs.default.env-vars]
DBDRIVER = "psycopg3"
DBHOST = "localhost"
DBPORT = "5432"
DBDATABASE = "test_db"
DBUSER = "dbuser"
DBPASSWORD = "secret"
[envs.default.scripts]
test = "pytest {args:src/tests}"
```

```bash
hatch run test
```

### Using poethepoet

```toml
[env]
DBDRIVER = "psycopg3"
DBHOST = "127.0.0.1"
DBPORT = "30000"
DBDATABASE = "test_db"
DBUSER = "dbuser"
DBPASSWORD = "secret"
[tasks.test]
cmd = "pytest src/tests"
```

```bash
uv run poe test
```

## Connection configuration

Like [Default configuration](#default-configuration), but final: env vars and defaults are no longer applied.

```python
@pytest.fixture(scope="module")
def database_kwargs():
    yield {
        'dbtype': 'psycopg3',
        'host': '127.0.0.1',
        'port': '5432',
        'database': 'test_db',
        'user': 'dbuser',
        'password': 'secret',
    }
```

## Database string

Override `database_string` with your database of choice.
Note that this will bypass connection string validation.

```python
@pytest.fixture(scope="module")
def database_string(database_kwargs, database_params):
    yield 'psycopg3://dbuser:secret@127.0.0.1:5432/test_db'
```

## Database Instance

If full configuration control is required, override the following:

```python
from playhouse.postgres_ext import Psycopg3Database

@pytest.fixture(scope="module")
def setup_database():
    database = Psycopg3Database(
        'test_db', host='127.0.0.1', port=5432, user='dbuser', password='secret',
    )
    with database.connection_context():
        yield database
```
