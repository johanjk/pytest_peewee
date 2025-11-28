
# Fixtures

Available fixtures:

```python
def test_fixutures(
    database_default_kwargs,
    database_default_envvar,
    database_kwargs,
    database_params,
    database_string,

    setup_database,

    pre_hook_database,
    post_hook_database,

    pre_transaction_database,
    post_transaction_database,

    transaction,
    database,

    sqlite,
    postgres,
    mysql,
    cockroach,
):
    pass
```

## Fixture flow

```mermaid
flowchart TD;
  DDK["database_default_kwargs"];
  DE["database_default_envvar"];
  DK["database_kwargs"];
  DP["database_params"];
  DS["database_string"];
  SD["setup_database"];

  PH0["pre_hook_database"];
  PH1["post_hook_database"];
  PT0["pre_transaction_database"];
  PT1["post_transaction_database"];
  T["transaction"];
  D["database"];

  DDK --> DK;
  DE --> DK;
  DK --> DS;
  DK --> DP;
  DP --> DS;
  DS --> SD;

  SD --> PH0;
  PH0 --> PH1;
  PH1 --> PT0;
  PT0 --> PT1;
  PT1 --> T;
  T --> D;
```
