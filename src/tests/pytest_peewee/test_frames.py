import re

import peewee as pw
import pytest

from pytest_peewee import _frames as frames


@pytest.mark.parametrize(("args", "config", "shown"), [
    pytest.param((), None, False, id="default"),
    pytest.param((), "frames/traceback_full.toml", True, id="full"),
    pytest.param(("--fulltrace",), None, True, id="fulltrace"),
])
def test_traceback(copy_testers, args: tuple[str, ...], config: str | None, shown: bool):
    """Failed query tracebacks leave out peewee's frames, noted under the query; not when full or with --fulltrace."""
    files = {"test_failed.py": "report/failed_query.py"} | ({"pyproject.toml": config} if config else {})
    pytester = copy_testers(files)
    result = pytester.runpytest("--color=no", *args)
    result.assert_outcomes(passed=1, failed=1)

    failure = result.stdout.str().split("_ test_unexpected_error _", 1)[1].split("peewee query call", 1)[0]
    assert ("peewee.py:" in failure) == shown
    assert re.search(r"^test_failed\.py:\d+: \w+Error$", failure, re.MULTILINE) or shown  # raised in the test
    assert ("During handling of the above exception" in failure) == shown  # the driver error peewee re-raises
    section = result.stdout.str().split("peewee query call", 1)[1]
    assert (f"\n{frames.HIDDEN_FRAMES}\n" in section) != shown


def test_traceback_note_colors(copy_testers):
    """With colors, the option showing hidden frames is colored like the file names."""
    pytester = copy_testers({"test_failed.py": "report/failed_query.py"})
    result = pytester.runpytest("--color=yes")
    assert "show them with \x1b[36m-o peewee_traceback=full\x1b[0m" in result.stdout.str()


def test_invalid_traceback(copy_testers):
    """Bad 'peewee_traceback' values are a usage error."""
    files = {"pyproject.toml": "frames/traceback_invalid.toml", "test_failed.py": "report/failed_query.py"}
    pytester = copy_testers(files)
    result = pytester.runpytest()
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "peewee_traceback must be one of" in result.stderr.str()


class FailingField(pw.Field):
    """Project code called back by peewee, raising."""

    field_type = "INT"

    def db_value(self, value: object) -> object:  # ruff: ignore[D102, PLR6301]
        msg = "bad value"
        raise ValueError(msg)


class Callback(pw.Model):  # ruff: ignore[D101]
    value = FailingField()


def test_query_modules_keep_callbacks(database):
    """Peewee's frames are hidden, project code called back by it is not."""
    with pytest.raises(ValueError, match="bad value") as excinfo:
        Callback.insert(value=1).execute()
    names = {module["__name__"] for module in frames.query_modules(excinfo.traceback)}
    assert "peewee" in names
    assert __name__ not in names  # the test and db_value
