"""Plugin hooks: ini options, and the global patches of a pytest session."""

from typing import TYPE_CHECKING, Literal, get_args

import pytest

from pytest_peewee import console, redirect, report

if TYPE_CHECKING:
    from collections.abc import Iterator

type ScopeName = Literal["session", "package", "module"]
type UnavailablePolicy = Literal["xfail", "skip", "fail"]

_patches = pytest.StashKey[pytest.MonkeyPatch]()
"""Global patches of this config: database redirect and query debug helpers."""

REDIRECT = pytest.StashKey[redirect.Redirect]()
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
        "Failed queries, .print() and .lint(): framed (panel, line numbers) or plain (copyable).",
        default="framed",
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


def pytest_configure(config: pytest.Config) -> None:
    """Validate options, then install the database redirect and query debug helpers.

    They are patched with monkeypatch, so a nested session (pytester) restores the outer one's.
    """
    value = config.getini("peewee_unavailable")
    if value not in get_args(UnavailablePolicy.__value__):
        msg = f"peewee_unavailable must be one of {get_args(UnavailablePolicy.__value__)}, got {value!r}"
        raise pytest.UsageError(msg)
    style = config.getini("peewee_report")
    if style not in console.REPORT_STYLES:
        msg = f"peewee_report must be one of {console.REPORT_STYLES}, got {style!r}"
        raise pytest.UsageError(msg)

    mp = pytest.MonkeyPatch()
    config.stash[_patches] = mp
    config.stash[REDIRECT] = redirect.install(mp)
    report.install_helpers(mp, config.stash[REDIRECT], style)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Undo `pytest_configure`, if it got to patch."""
    if _patches in config.stash:
        config.stash[_patches].undo()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item) -> Iterator[None]:
    """Hide the module wide database from tests not requesting it."""
    uses = "module_database" in getattr(item, "fixturenames", ())
    with item.config.stash[REDIRECT].hidden(frozenset() if uses else frozenset({"module_database"})):
        yield


def scope(fixture_name: str, config: pytest.Config) -> ScopeName:  # ruff: ignore[ARG001]
    """Scope of connection and schema fixtures, from the 'peewee_scope' ini option.

    Use it when overriding those fixtures: `@pytest.fixture(scope=pytest_peewee.scope)`.
    """
    value = config.getini("peewee_scope")
    if value not in get_args(ScopeName.__value__):
        msg = f"peewee_scope must be one of {get_args(ScopeName.__value__)}, got {value!r}"
        raise pytest.UsageError(msg)
    return value
