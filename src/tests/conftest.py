import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

pytest_plugins = ["pytester"]


@pytest.fixture(scope="session")
def toplevel_path() -> Iterator[Path]:
    """Top level directory of project."""
    yield Path(__file__).parents[2]


@pytest.hookimpl(tryfirst=True)
def pytest_configure() -> None:
    """Test output expect agent integration is unset."""
    os.environ.pop("AI_AGENT", None)
