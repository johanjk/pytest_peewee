# Fixtures

Available fixtures:

```python
def test_fixtures(
    # connection (scope: 'peewee_scope' ini option, default module)
    database_default_kwargs,
    database_default_envvar,
    database_kwargs,
    database_params,
    database_string,
    setup_database,
    database_from_env,

    # schema and isolation settings (scope: 'peewee_scope')
    database_models,
    database_redirect,
    database_isolation,
    setup_schema,

    # module wide transaction (scope: module)
    module_database,

    # per test savepoint (scope: function)
    database,

    # Mutually exclusive group of fixtures
    sqlite,
    postgres,
    mysql,
    cockroach,
):
    pass
```

| Fixture | Purpose |
| --- | --- |
| `database_models` | Models whose tables `setup_schema` creates once, and drops after. |
| `database_redirect` | `{source_db: test_db}` for multi-database projects; the test databases are rolled back like `database`. |
| `database_from_env` | Makes extra test databases, configured from env vars with a prefix (e.g. `ANALYTICS_DBDRIVER`). |
| `database_isolation` | `strict`, `warn` or `off`, from the `peewee_isolation` ini option. |
| `setup_schema` | Creates the tables outside any test transaction. Override to run migrations. |
| `module_database` | Module wide transaction (rolled back after the module). Override to add shared data. |
| `database` | Per test savepoint, rolled back after the test. Models and queries are redirected to it. |
| `sqlite`, `postgres`, `mysql`, `cockroach` | `database`, skipping the test on other databases. |

## Fixture flow

```mermaid
flowchart TD;
  DDK["database_default_kwargs"];
  DE["database_default_envvar"];
  DK["database_kwargs"];
  DP["database_params"];
  DS["database_string"];
  SD["setup_database"];
  FE["database_from_env"];

  DM["database_models"];
  DR["database_redirect"];
  DI["database_isolation"];
  SS["setup_schema"];
  MD["module_database"];
  D["database"];
  DB["sqlite / postgres / mysql / cockroach"];

  DDK --> DK;
  DE --> DK;
  DK --> DS;
  DK --> DP;
  DP --> DS;
  DS --> SD;
  FE -. test databases .-> DR;

  SD --> SS;
  DM --> SS;
  DR --> SS;
  SS --> MD;
  DR --> MD;
  DI --> MD;

  MD --> D;
  DR --> D;
  DI --> D;
  D --> DB;
```
