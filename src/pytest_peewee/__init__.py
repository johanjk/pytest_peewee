"""pytest-peewee: pytest extensions for peewee."""

from .isolation import IsolationError, IsolationWarning, RollbackDatabase
from .plugin import (
    cockroach,
    database,
    database_default_envvar,
    database_default_kwargs,
    database_from_env,
    database_isolation,
    database_kwargs,
    database_models,
    database_params,
    database_redirect,
    database_string,
    module_database,
    mysql,
    postgres,
    pytest_addoption,
    pytest_configure,
    pytest_runtest_protocol,
    scope,
    setup_database,
    setup_schema,
    sqlite,
)
from .report import pytest_runtest_makereport
from .types import DebugContext, DebugQuery
from .version import __version__, __version_tuple__

__all__ = [
    "DebugContext",
    "DebugQuery",
    "IsolationError",
    "IsolationWarning",
    "RollbackDatabase",
    "cockroach",
    "database",
    "database_default_envvar",
    "database_default_kwargs",
    "database_from_env",
    "database_isolation",
    "database_kwargs",
    "database_models",
    "database_params",
    "database_redirect",
    "database_string",
    "module_database",
    "mysql",
    "postgres",
    "scope",
    "setup_database",
    "setup_schema",
    "sqlite",
]
