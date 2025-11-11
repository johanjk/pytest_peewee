import peewee as pw
import pytest


class OtherTable(pw.Model):
    x = pw.IntegerField()
    y = pw.TextField()


@pytest.fixture(scope="function")
def database(database):
    OtherTable.create_table()
    yield database


def maybe_bad_query(fail: bool) -> pw.Query:
    a = OtherTable.alias("sq")
    subq = a.select(a.x)

    on_clause = a.x if fail else subq.c.x
    # Target the inner name or the correct outer name

    return (
        OtherTable
        .select()
        .join(subq, on=(on_clause == OtherTable.x))
    )


def test_query_lint_ok(database):
    """Expect lint ok error."""
    assert maybe_bad_query(False).lint()


def test_query_lint_err(capsys, database):
    """Expect lint error."""
    assert not maybe_bad_query(True).lint()  # Lint should fail

    stdout = capsys.readouterr().out
    print(stdout)
    assert "RF01" in stdout and "Reference '\"sq\".\"x\"'" in stdout  # noqa: PT018
    assert stdout.count(":") == 1  # Only one lint error


def test_print(capsys, database):
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
    │ [...]/tests/pytest_peewee/test_console.py:46                                 │
    ╰──────────────────────────────────────────────────────────────────────────────╯
    """
    assert __file__ in stdout
    assert len(stdout.split("\n")) == len(exp.split("\n"))
