import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

ENV_VAR: re.Pattern[str] = re.compile(
    r"""
    \$
    (?:
        ([A-Za-z_]\w*)      # $NAME, group 1
      | \{([A-Za-z_]\w*)\}  # ${NAME}, group 2
    )
    """,
    re.VERBOSE,
)


def _env_value(match: re.Match[str]) -> str:
    # Unset variables become empty, so 'database_kwargs' falls back to the defaults.
    return os.environ.get(match[1] or match[2], "")


def parse_env(kwargs: Mapping[str, str]) -> dict[str, str]:
    """Copy of `kwargs`, with env var references ($NAME or ${NAME}) in its values replaced."""
    return {key: ENV_VAR.sub(_env_value, value) for key, value in kwargs.items()}
