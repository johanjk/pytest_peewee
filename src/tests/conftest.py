import os
from collections.abc import Iterator
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture(scope="session")
def toplevel_path() -> Iterator[Path]:
    """Top level directory of project."""
    yield Path(__file__).parents[2]


@pytest.hookimpl(tryfirst=True)
def pytest_configure() -> None:
    """Test output expect agent integration is unset."""
    os.environ.pop("AI_AGENT", None)
