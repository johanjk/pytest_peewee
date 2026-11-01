"""pytest-peewee: pytest extensions for peewee."""

from ._isolation import IsolationError, IsolationPolicy, IsolationWarning, RollbackDatabase
from ._plugin import (
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
from ._plugin.connection import DatabaseFactory
from ._redirect import DatabaseMap
from ._report import pytest_runtest_makereport
from ._types import DebugContext, DebugHelper, DebugQuery
from .version import __version__, __version_tuple__

__all__ = [
    "DatabaseFactory",
    "DatabaseMap",
    "DebugContext",
    "DebugHelper",
    "DebugQuery",
    "IsolationError",
    "IsolationPolicy",
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
