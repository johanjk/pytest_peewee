from collections.abc import Iterator
from pathlib import Path

import pytest


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
