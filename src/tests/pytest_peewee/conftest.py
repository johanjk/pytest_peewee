from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(scope="session")
def pytester_tests() -> Iterator[Path]:
    """Location of pytester files."""
    yield Path(__file__).parent / "tester"


@pytest.fixture
def run_testpath(pytester: pytest.Pytester, pytester_tests: Path):
    """Run a test wrapped in pytester."""

    def inner(file: str):
        pytester.makepyfile((pytester_tests / file).read_text(encoding="utf-8"))
        return pytester.runpytest()

    return inner


@pytest.fixture
def copy_testers(pytester: pytest.Pytester, pytester_tests: Path):
    """Copy tester files into pytester, as `{destination: tester file}`."""

    def inner(files: dict[str, str]) -> pytest.Pytester:
        for destination, source in files.items():
            (pytester.path / destination).write_text(
                (pytester_tests / source).read_text(encoding="utf-8"), encoding="utf-8",
            )
        return pytester

    return inner
