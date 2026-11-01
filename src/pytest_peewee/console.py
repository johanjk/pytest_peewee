import os
import traceback
import warnings
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import peewee as pw
from rich.console import Console, Group, RenderableType
from rich.containers import Lines
from rich.panel import Panel
from rich.style import Style
from rich.syntax import Syntax
from rich.text import Text

from . import fmt
from .lint_highlight import lint_message

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import FrameType

type ReportStyle = Literal["framed", "plain"]
REPORT_STYLES: tuple[ReportStyle, ...] = ("framed", "plain")


def _frame(*renderables: RenderableType | None, style: ReportStyle) -> RenderableType:
    """Group `renderables`, in a panel unless the style is plain."""
    group = Group(*[r for r in renderables if r is not None])
    return Panel(group) if style == "framed" else group


def agent() -> bool:
    """Whether an AI agent runs the tests, by the `AI_AGENT` env var."""
    return bool(os.environ.get("AI_AGENT"))


_UNWRAPPED = 100_000
"""Console width that never wraps; plain output is not padded to it."""


def width(style: ReportStyle) -> int | None:
    """Console width for `style`: unwrapped for AI agents with plain reports, else that of the terminal (None)."""
    return _UNWRAPPED if agent() and style == "plain" else None


def console(style: ReportStyle = "framed") -> Console:
    """Pytest compatible console printer; without colors for AI agents, and unwrapped when plain."""
    return Console(color_system=None if agent() else "truecolor", width=width(style))


def colored(out: Console) -> bool:
    """Whether `out` prints colors."""
    return out.color_system is not None and not out.no_color


def dialect(database: pw.Database) -> str | None:
    """Highlight using a closest match dialect.

    See: https://pygments.org/languages/ for supported dialects
    """
    match database:
        case pw.PostgresqlDatabase():
            return "postgres"
        case pw.MySQLDatabase():
            return "mysql"
        case pw.SqliteDatabase():
            return None
        case _:
            msg = f"Database dialect '{type(database)}' not supported, falling back to base ANSI."
            warnings.warn(msg, stacklevel=1)
    return None


def highlight(s: str, dialect: str | None = None, style: ReportStyle = "framed") -> Syntax:
    """Colored syntax highlighting."""
    if style == "framed":
        return Syntax(s, dialect or "SQL", line_numbers=("\n" in s), word_wrap=True)
    # the default background is not padded to the full width, so copying gives no trailing spaces
    return Syntax(s, dialect or "SQL", word_wrap=True, background_color="default")


# Packages skipped when locating the code running a query.
_LIBRARIES = ("peewee", "playhouse", "pytest_peewee", "_pytest", "pytest", "pluggy")


def _is_library(frame: FrameType) -> bool:
    module = frame.f_globals.get("__name__", "")
    return not module or module.split(".")[0] in _LIBRARIES


type Location = tuple[Path, int]
"""Absolute file and line number."""


def find_caller(frames: Iterable[tuple[FrameType, int]]) -> Location | None:
    """Location of the code calling into the libraries.

    `frames` go from the innermost outwards; the caller is the first frame outside the
    libraries after passing through them, skipping e.g. database driver frames below peewee.
    """
    called = False
    for frame, lineno in frames:
        if _is_library(frame):
            called = True
        elif called:
            return Path(frame.f_code.co_filename).absolute(), lineno
    return None


def location_text(location: Location) -> Text:
    """`Called from: file:line`, the file relative to the working dir and linked (OSC 8) to the line.

    The link fragment `#L<line>` opens the line in e.g. VS Code; other terminals may open just the file.
    """
    path, lineno = location
    shown = path
    with suppress(ValueError):
        shown = path.relative_to(Path.cwd())
        # Fallback to abs path if not relative
    return Text.assemble(
        "Called from: ",
        Text(str(shown), Style(color="cyan", link=f"{path.as_uri()}#L{lineno}")),
        ":",
        Text(str(lineno), Style(color="yellow")),
        overflow="fold",
    )


def caller_info() -> Text | None:
    """`Called from: file:line` of the code calling into the libraries."""
    location = find_caller(traceback.walk_stack(None))
    return location_text(location) if location else None


def raised_at(exc: BaseException) -> Location | None:
    """Location of the code raising `exc`, through the libraries."""
    return find_caller(reversed(list(traceback.walk_tb(exc.__traceback__))))


def highlight_lint(s: Syntax, warns: list[fmt.LintInfo]) -> None:
    """Highlight area of linting errors."""
    style = Style(bgcolor="red")
    for w in warns:
        start = (
            w["start_line_no"],
            w["start_line_pos"] - 1,
        )
        end = (
            w["end_line_no"],
            w["end_line_pos"] - 1,
        )
        s.stylize_range(style, start=start, end=end)


def _span(warn: fmt.LintInfo) -> str:
    """`L<line>:<from>-<to>` of a linting error, columns inclusive; `L<line>:<col>-L<line>:<col>` across lines."""
    line, start = warn["start_line_no"], warn["start_line_pos"]
    end_line, end = warn["end_line_no"], warn["end_line_pos"] - 1  # sqlfluff's end is exclusive
    if end_line != line:
        return f"L{line}:{start}-L{end_line}:{end}"
    return f"L{line}:{start}-{end}" if end > start else f"L{line}:{start}"


def lint_messages(warns: list[fmt.LintInfo], *, positions: bool = False) -> list[tuple[str, str]]:
    """Unique `(code, description)` of linting errors.

    With `positions`, the code is prefixed by the span of each occurrence, e.g. `L7:19-21 RF01`;
    for reports without colors, where the error location is not highlighted.
    """
    found: dict[tuple[str, str], list[str]] = {}
    for w in warns:
        found.setdefault((w["code"], w["description"]), []).append(_span(w))
    if not positions:
        return list(found)
    return [(" ".join([*dict.fromkeys(locs), code]), desc) for (code, desc), locs in found.items()]


def query_view(  # ruff: ignore[PLR0913]
    query: pw.Query,
    database: pw.Database,
    subtext: str | Text | None = None,
    caller: Text | None = None,
    *,
    lint: bool = False,
    positions: bool = False,
    style: ReportStyle = "framed",
) -> RenderableType:
    """Formatted and highlighted query, with `caller`, linting errors (when `lint`) and `subtext` under it.

    With `positions`, the linting errors start with their span in the query, e.g. `L7:19-21`.
    """
    sql, warns = fmt.lint_query(query, database) if lint else (fmt.render(query, database), [])
    syntax = highlight(sql, dialect(database), style)
    highlight_lint(syntax, warns)

    errors = None
    if warns:
        red = Style(color="red")
        errors = Lines(
            Text.assemble(Text(code, style=red), ": ", lint_message(desc, dialect(database)))
            for code, desc in lint_messages(warns, positions=positions)
        )
        subtext = Text.assemble("\n", subtext) if subtext else subtext
    return _frame(syntax, caller, errors, subtext, style=style)


def print_query(
    query: pw.Query, database: pw.Database, subtext: str | None = None, *, style: ReportStyle = "framed",
) -> None:
    """Pretty print a query."""
    out = console(style)
    out.print(query_view(query, database, subtext, caller_info(), positions=not colored(out), style=style))


def print_lint(
    query: pw.Query, database: pw.Database, subtext: str | None = None, *, style: ReportStyle = "framed",
) -> bool:
    """Pretty print a query with its linting errors, if any.

    Returns:
        True if linting found no problems.
    """
    _, warns = fmt.lint_query(query, database)
    if not warns:
        return True
    out = console(style)
    out.print(query_view(query, database, subtext, caller_info(), lint=True, positions=not colored(out), style=style))
    return False
