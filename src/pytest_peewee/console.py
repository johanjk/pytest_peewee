from inspect import getframeinfo, stack

import peewee as pw
from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.syntax import Syntax
from rich.text import Lines, Text

from . import fmt


def console():
    """Pytest compatible console printer."""
    return Console(color_system="truecolor")


def highlight(s: str, dialect: str | None = None) -> Syntax:
    """Colored syntax highlighting."""
    return Syntax(s, dialect or "SQL", line_numbers=("\n" in s), word_wrap=True)


def caller_info(stacklevel: int):
    """File and line info of caller."""
    caller = getframeinfo(stack()[stacklevel][0])
    style = Style(color="red")
    return Text.assemble(Text(caller.filename, style), ":", str(caller.lineno))


def print_query(query: pw.Query, database: pw.Database, stacklevel: int | None = 1):
    """Pretty print a query."""
    d = highlight(fmt.render(query, database), fmt.dialect(database))
    if stacklevel is not None:
        d = Group(
            d,
            caller_info(stacklevel + 1),
        )
    console().print(Panel(d))


def highlight_lint(s: Syntax, warns: list[dict[str, int]]) -> None:
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


def print_lint(query: pw.Query, database: pw.Database) -> bool:
    """Pretty print a query and possible linting errors."""
    s, f = fmt.lint_query(query, database)
    if not f:
        return True

    s = highlight(s, fmt.dialect(database))
    highlight_lint(s, f)

    errs = dict.fromkeys((x["code"], x["description"]) for x in f)
    # remove duplicate msgs

    style = Style(color="red")
    errs = Lines(Text.assemble(Text(x[0], style=style), ": ", x[1]) for x in errs)
    console().print(Panel(Group(s, errs)))
    return False
