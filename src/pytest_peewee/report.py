"""Query debug helpers and failure reports."""

import io
import re
from contextlib import suppress
from typing import TYPE_CHECKING

import peewee as pw
import pytest
from rich.console import Console
from rich.style import Style
from rich.text import Text

from . import console, fmt
from .isolation import FAILED_QUERY
from .output import run_dir

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator
    from pathlib import Path

    from .redirect import Redirect


def report_style(config: pytest.Config) -> console.ReportStyle:
    """The 'peewee_report' ini option; when unset, plain for AI agents and framed otherwise."""
    style = config.getini("peewee_report")
    if style is None:
        return "plain" if console.agent() else "framed"
    if style not in console.REPORT_STYLES:
        msg = f"peewee_report must be one of {console.REPORT_STYLES}, got {style!r}"
        raise pytest.UsageError(msg)
    return style


def install_helpers(mp: pytest.MonkeyPatch, redirect: Redirect, style: console.ReportStyle) -> None:
    """Add `.print()` and `.lint()` to peewee queries, printing in `style`, undone by `mp`.

    Unbound queries use the active test database of `redirect`.
    """
    def database_of(query: pw.Query) -> pw.Database:
        db = getattr(query, "_database", None) or redirect.current()
        if db is None:
            msg = "Query is not bound to a database, and no test database is active."
            raise pw.InterfaceError(msg)
        return db

    def lint(self: pw.Query, subtext: str | None = None) -> bool:
        return console.print_lint(self, database_of(self), subtext, style=style)

    def print_(self: pw.Query, subtext: str | None = None) -> None:
        console.print_query(self, database_of(self), subtext, style=style)

    binds = {
        "print": print_,
        "lint": lint,
    }
    for cls in (pw.Query, pw.Context):
        for name, func in binds.items():
            mp.setattr(cls, name, func, raising=False)


def _exception_chain(exc: BaseException | None) -> Iterator[BaseException]:
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def _comment(text: str) -> str:
    return "\n".join(f"-- {line}".rstrip() for line in text.splitlines())


def write_query_file(  # ruff: ignore[PLR0913]
    item: pytest.Item,
    when: str,
    query: pw.Query,
    database: pw.Database,
    subtext: str,
    *,
    caller: console.Location | None = None,
) -> Path:
    """Write the formatted query to `<output>/run-<N>/<test id>/query.sql`.

    The caller (full path), lint errors (by line and columns) and `subtext` are added as comments under the query.
    """
    sql, warns = fmt.lint_query(query, database)
    notes = [
        f"{code}: {description}"
        for code, description
        in console.lint_messages(warns, positions=True)
    ]
    if caller:
        notes.insert(0, f"Called from: {caller[0]}:{caller[1]}")
    comments = "\n".join(_comment(note) for note in [*notes, subtext])

    folder = run_dir(item.config) / re.sub(r"[^\w.]+", "-", item.nodeid).strip("-")
    folder.mkdir(exist_ok=True)
    path = folder / ("query.sql" if when == "call" else f"query-{when}.sql")
    path.write_text(f"{sql.rstrip()}\n\n{comments}\n", encoding="utf-8")
    return path


def _query_link(config: pytest.Config, path: Path, *, linked: bool) -> Text:
    """`Query file: <name>`, colored like the caller's file and linked (OSC 8) to the file.

    Without links, the path to open: relative to the invocation dir, or the full path.
    """
    if linked:
        return Text.assemble("Query file: ", Text(path.name, Style(color="cyan", link=path.as_uri())))
    shown = path
    with suppress(ValueError):
        shown = path.relative_to(config.invocation_params.dir)
    return Text(f"Query file: {shown}")


def _error_text(exc: BaseException) -> Text:
    return Text.assemble(Text(type(exc).__name__, Style(color="red", bold=True)), f": {exc}")


def render_failed_query(item: pytest.Item, error: BaseException, when: str = "call") -> str | None:
    """Render the failed query attached to `error` (or its causes), if any.

    The query is also written to a .sql file, linked under the rendered query; not for AI agents,
    as the report holds the same query and errors.
    For AI agents, the error (in the traceback above) is left out.
    """
    for exc in _exception_chain(error):
        info = getattr(exc, FAILED_QUERY, None)
        if info is None:
            continue
        query, database = info
        subtext = f"{type(exc).__name__}: {exc}"
        tw = item.config.get_terminal_writer()
        style = report_style(item.config)
        buffer = io.StringIO()
        out = Console(
            file=buffer,
            force_terminal=tw.hasmarkup,
            color_system="truecolor" if tw.hasmarkup else None,
            width=console.width(style) or tw.fullwidth,
        )
        caller = console.raised_at(exc)
        agent = console.agent()
        rendered = False
        with suppress(Exception):  # never break the report; the raw query is in the exception note
            caller_view = console.location_text(caller) if caller else None
            view = console.query_view(
                query, database, None if agent else _error_text(exc), caller_view,
                lint=True, positions=not tw.hasmarkup, style=style,
            )
            out.print(view)
            rendered = True
        if not rendered:
            return None
        if not agent:  # agents read the query and errors from the report
            with suppress(Exception):  # the file is best effort
                path = write_query_file(item, when, query, database, subtext, caller=caller)
                out.print(_query_link(item.config, path, linked=tw.hasmarkup), soft_wrap=True)
        return buffer.getvalue()
    return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None],
) -> Generator[None, pytest.TestReport]:
    """Add the formatted and linted failed query to failing test reports."""
    outcome = yield
    report: pytest.TestReport = outcome.get_result()  # type: ignore[attr-defined]
    if report.failed and call.excinfo is not None:
        rendered = render_failed_query(item, call.excinfo.value, call.when)
        if rendered:
            report.sections.append((f"peewee query {call.when}", rendered))
