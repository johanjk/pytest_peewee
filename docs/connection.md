# Configure database connection

## Default configuration

Set a default configuration that matches your specific development environment.
Note that env vars will replace defaults, if present.

```python
import pytest

@pytest.fixture(scope="module")
def database_default_kwargs():
    yield {
        'dbtype': 'postgresext',
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
export DBDRIVER="postgresext"
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

### Using hatch `hatch.toml`:

```toml
[envs.default.env-vars]
DBDRIVER = "postgresext"
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


## Connection configuration

This is equivalent to [Default configuration](#default-configuration), but happens after env var replacement.

```python
@pytest.fixture(scope="module")
def database_kwargs(database_envvar, database_default_kwargs):
    yield {
        'dbtype': 'postgresext',
        'host': '127.0.0.1',
        'port': '5432',
        'database': 'test_db',
        'user': 'dbuser',
        'password': 'secret',
    }
```

## Database string

Override `database_string` with your database of choice.

```python
@pytest.fixture(scope="module")
def database_string(database_kwargs, database_params):
    yield 'postgresext//dbuser:secret@127.0.0.1:5432/test_db'
```

## Database Instance

If full configuration control is required, override the following:

```python
@pytest.fixture(scope="module")
def setup_database(request, database_string):
    yield pw.Database('test_db')
```
