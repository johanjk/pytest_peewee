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


def highlight(s: str) -> Syntax:
    """Colored syntax highlighting."""
    return Syntax(s, "sql", line_numbers=("\n" in s))


def caller_info(stacklevel: int):
    caller = getframeinfo(stack()[stacklevel][0])
    style = Style(color="red")
    return Text.assemble(Text(caller.filename, style), ":", str(caller.lineno))


def print_query(query: pw.Query, stacklevel: int | None = 1):
    d = highlight(fmt.render(query))
    if stacklevel is not None:
        d = Group(
            d,
            caller_info(stacklevel+1),
        )
    console().print(Panel(d))


def print_lint(query: pw.Query, database: pw.Database) -> bool:
    s, f = fmt.lint_query(query, database)
    if not f:
        return True

    s = highlight(s)
    style = Style(bgcolor="red")
    for x in f:
        start = (
            x["start_line_no"],
            x["start_line_pos"]-1,
        )
        end = (
            x["end_line_no"],
            x["end_line_pos"]-1,
        )
        s.stylize_range(style, start=start, end=end)

    errs = dict.fromkeys((x["code"], x["description"]) for x in f)
    style = Style(color="red")
    errs = Lines(Text.assemble(Text(x[0], style=style), ": ", x[1]) for x in errs)
    console().print(Panel(Group(s, errs)))
    return False
