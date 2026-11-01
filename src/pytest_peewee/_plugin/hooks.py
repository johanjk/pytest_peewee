"""Plugin hooks: ini options, and the global patches of a pytest session."""

from typing import TYPE_CHECKING, Literal, cast, get_args

import pytest

from .._console import agent
from .._frames import traceback_style
from .._redirect import Redirect
from .._redirect import install as install_redirect
from .._report import install_helpers, report_style

if TYPE_CHECKING:
    from collections.abc import Generator

type ScopeName = Literal["session", "package", "module"]
type UnavailablePolicy = Literal["xfail", "skip", "fail"]


REDIRECT = pytest.StashKey[Redirect]()
"""Redirect frames of this session."""


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register ini options."""
    parser.addini(
        "peewee_scope",
        "Scope of the connection and schema fixtures: session, package or module.",
        default="module",
    )
    parser.addini(
        "peewee_isolation",
        "Statements breaking test isolation (COMMIT, MySQL DDL): strict (error), warn or off.",
        default="strict",
    )
    parser.addini(
        "peewee_report",
        "Failed queries, .print() and .lint(): framed (panel, line numbers) or plain (copyable). "
        "Unset: plain when the AI_AGENT env var is set, framed otherwise.",
        default=None,
    )
    parser.addini(
        "peewee_traceback",
        "Tracebacks of failed queries: short (without peewee and driver frames) or full. --fulltrace shows them full.",
        default="short",
    )
    parser.addini(
        "peewee_output",
        "Folder for failure artifacts (failed queries as .sql files), relative to the rootdir.",
        default="test-results",
    )
    parser.addini(
        "peewee_unavailable",
        "Unavailable or unconfigured database: xfail (an error with --runxfail), skip or fail.",
        default="xfail",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Validate options, then install the database redirect and query debug helpers.

    They are patched with monkeypatch, so a nested session (pytester) restores the outer one's.
    For AI agents, colors are turned off, before pytest's terminal reporter reads the option.
    """
    if agent():
        config.option.color = "no"
    value = config.getini("peewee_unavailable")
    if value not in get_args(UnavailablePolicy.__value__):
        msg = f"peewee_unavailable must be one of {get_args(UnavailablePolicy.__value__)}, got {value!r}"
        raise pytest.UsageError(msg)
    style = report_style(config)
    traceback_style(config)  # validate

    mp = pytest.MonkeyPatch()
    config.add_cleanup(mp.undo)
    config.stash[REDIRECT] = install_redirect(mp)
    install_helpers(mp, config.stash[REDIRECT], style)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item: pytest.Item) -> Generator[None, object, object]:
    """Hide the module wide database from tests not requesting it."""
    uses = "module_database" in getattr(item, "fixturenames", ())
    with item.config.stash[REDIRECT].hidden(frozenset() if uses else frozenset({"module_database"})):
        return (yield)


def scope(fixture_name: str, config: pytest.Config) -> ScopeName:  # ruff: ignore[ARG001]
    """Scope of connection and schema fixtures, from the 'peewee_scope' ini option.

    Use it when overriding those fixtures: `@pytest.fixture(scope=pytest_peewee.scope)`.
    """
    value = config.getini("peewee_scope")
    if value not in get_args(ScopeName.__value__):
        msg = f"peewee_scope must be one of {get_args(ScopeName.__value__)}, got {value!r}"
        raise pytest.UsageError(msg)
    return cast(ScopeName, value)
