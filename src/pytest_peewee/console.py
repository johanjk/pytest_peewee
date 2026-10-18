import inspect
import warnings
from collections.abc import Sequence

import peewee as pw
from rich.console import Console, Group
from rich.containers import Lines
from rich.panel import Panel
from rich.style import Style
from rich.syntax import Syntax
from rich.text import Text

from . import fmt


def console() -> Console:
    """Pytest compatible console printer."""
    return Console(color_system="truecolor")


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


def highlight(s: str, dialect: str | None = None) -> Syntax:
    """Colored syntax highlighting."""
    return Syntax(s, dialect or "SQL", line_numbers=("\n" in s), word_wrap=True)


def get_external_caller_info(package_names: Sequence[str]) -> inspect.Traceback | None:
    package_prefixes = tuple(f"{pkg}." for pkg in package_names)

    frame = inspect.currentframe()
    if not frame:
        return None

    while frame := frame.f_back:
        module_name = frame.f_globals.get('__name__', '')

        if module_name:
            is_excluded = (
                module_name in package_names or
                module_name.startswith(package_prefixes)
            )

            if not is_excluded:
                return inspect.getframeinfo(frame)

    return None


def caller_info() -> Text | None:
    """File and line info of caller."""
    caller = get_external_caller_info(["peewee", "pytest_peewee", "_pytest", "pytest", "pluggy"])
    if caller is None:
        return None
    style = Style(color="red")
    return Text.assemble(Text(caller.filename, style), ":", str(caller.lineno), overflow="fold")


def print_query(query: pw.Query, database: pw.Database, subtext: str | None = None) -> None:
    """Pretty print a query."""
    d = highlight(fmt.render(query, database), dialect(database))
    g = [
        d,
        caller_info(),
        subtext
    ]
    d = Group(*[o for o in g if o is not None])
    console().print(Panel(d))


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


def print_lint(query: pw.Query, database: pw.Database, subtext: str | None = None) -> bool:
    """Pretty print a query and possible linting errors."""
    s, f = fmt.lint_query(query, database)
    if not f:
        return True

    s = highlight(s, dialect(database))
    highlight_lint(s, f)

    errs = dict.fromkeys((x["code"], x["description"]) for x in f)
    # remove duplicate msgs

    style = Style(color="red")
    errs = Lines(Text.assemble(Text(x[0], style=style), ": ", x[1]) for x in errs)
    subtext = f"\n{subtext}" if subtext else subtext
    g = [s, errs, subtext]
    d = Group(*[o for o in g if o is not None])
    console().print(Panel(d))
    return False
