from pathlib import Path

import peewee as pw
import pytest
from rich.console import Console

from pytest_peewee import DebugQuery, RollbackDatabase


class OtherTable(pw.Model):  # noqa: D101
    x = pw.IntegerField()
    y = pw.TextField()


@pytest.fixture(scope="function")
def database(database):  # noqa: D103
    OtherTable.create_table()
    yield database
    if database.is_connection_usable():
        OtherTable.drop_table()


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


def test_query_lint_ok(database: RollbackDatabase):
    """Expect lint ok error."""
    assert maybe_bad_query(False).lint()


def test_query_lint_err(capsys: pytest.CaptureFixture[str], database: RollbackDatabase):
    """Expect lint error."""
    assert not maybe_bad_query(True).lint()  # Lint should fail

    stdout = capsys.readouterr().out
    print(stdout)
    match database:
        case pw.PostgresqlDatabase():
            assert "RF01" in stdout and "Reference '\"sq\".\"x\"'" in stdout  # noqa: PT018
        case pw.MySQLDatabase():
            assert "RF01" in stdout and "Reference '`sq`.`x`'" in stdout  # noqa: PT018
        case pw.SqliteDatabase():
            assert "RF01" in stdout and "Reference '\"sq\".\"x\"'" in stdout  # noqa: PT018
        case _:
            assert False
    assert stdout.count(":") == 1  # Only one lint error


def test_print(capsys: pytest.CaptureFixture[str], database: RollbackDatabase, monkeypatch: pytest.MonkeyPatch):
    """Check output is close to the expected query (color matching is not attempted)."""
    # disable colors for easier comparison
    with monkeypatch.context() as m:
        from pytest_peewee import console as c
        monkeypatch.setattr(c, "console", lambda: Console(color_system=None))

        maybe_bad_query(False).print()

    stdout = capsys.readouterr().out
    print(stdout)


    exp = """\
    ╭──────────────────────────────────────────────────────────────────────────────╮
    │   1 WITH t2 AS (SELECT "sq"."x" FROM "othertable" AS "sq")                   │
    │   2                                                                          │
    │   3 SELECT                                                                   │
    │   4     "t1"."id",                                                           │
    │   5     "t1"."x",                                                            │
    │   6     "t1"."y"                                                             │
    │   7 FROM "othertable" AS "t1"                                                │
    │   8 INNER JOIN t2 ON ("t1"."x" = "t2"."x")                                   │
    │ [...]/tests/pytest_peewee/test_console.py:67                                 │
    ╰──────────────────────────────────────────────────────────────────────────────╯
    """
    assert __file__[:c.console().width-4] in stdout
    # long filepath can be word_wrapped, slice first part - Panel size

    assert len(stdout.split("\n")) >= len(exp.split("\n"))
    # can be larger if filepath is longer than terminal width
