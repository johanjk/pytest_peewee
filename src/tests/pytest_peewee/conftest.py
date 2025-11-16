from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def pytester_tests() -> Iterator[Path]:
    """Location of pytester files."""
    yield Path(__file__).parent / "tester"


@pytest.fixture
def run_testpath(testdir: pytest.Testdir, pytester_tests: Path):
    """Run a test wrapped in pytester."""

    def inner(file: str):
        with open(pytester_tests / file, encoding="utf-8") as f:
            testdir.makepyfile(f.read())
        return testdir.runpytest()

    return inner
