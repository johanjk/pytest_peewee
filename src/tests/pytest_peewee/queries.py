"""Queries for the debug helper tests; `maybe_bad_query(False)` is valid, the rest fail to lint."""

from typing import TYPE_CHECKING

import peewee as pw

if TYPE_CHECKING:
    from pytest_peewee import DebugQuery


class OtherTable(pw.Model):  # ruff: ignore[D101]
    x = pw.IntegerField()
    y = pw.TextField()


def maybe_bad_query(fail: bool) -> DebugQuery:
    """Query with possible wrong selector."""
    a = OtherTable.alias("sq")
    subq = a.select(a.x)

    on_clause = a.x if fail else subq.c.x
    # Target the inner name or the correct outer name

    return (
        OtherTable
        .select()
        .join(subq, on=(on_clause == OtherTable.x))
    )


def compare_to_null() -> DebugQuery:
    """Comparison with NULL using '=' (CV05): keywords in the text and in double quotes."""
    return (
        OtherTable
        .select(OtherTable.x)
        .where(pw.Expression(OtherTable.x, "=", pw.SQL("NULL")))
    )


def unused_cte() -> DebugQuery:
    """CTE that is never used (ST03): an all-caps word that is no keyword, a quoted identifier in double quotes."""
    cte = OtherTable.select(OtherTable.x).cte("c")

    return (
        OtherTable
        .select(OtherTable.x)
        .with_cte(cte)
    )


def unparsable_with_string() -> DebugQuery:
    """Unparsable SQL next to a quoted string (PRS), which sqlfluff escapes in its message."""
    return (
        OtherTable
        .select(OtherTable.x)
        .where(pw.SQL("x x"), OtherTable.y == "it's")
    )


def wrong_selector() -> DebugQuery:
    """Join on the inner name of a subquery (RF01): quoted identifiers, a keyword in the text."""
    return maybe_bad_query(True)
