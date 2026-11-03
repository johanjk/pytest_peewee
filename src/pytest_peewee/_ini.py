"""Validated ini options."""

from typing import cast

import pytest


def ini_choice[T: str](config: pytest.Config, name: str, choices: tuple[T, ...]) -> T:
    """The ini option `name`, which must be one of `choices`."""
    value = config.getini(name)
    if value not in choices:
        msg = f"{name} must be one of {choices}, got {value!r}"
        raise pytest.UsageError(msg)
    return cast(T, value)
