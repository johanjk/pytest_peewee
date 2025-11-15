import os
import re

REGEX = r"\$([A-Z_][A-Z0-9_]+)"
envsub: re.Pattern[str] = re.compile(REGEX)

type NDict = dict[str, str | NDict]


def _env_replace(x: re.Match[str]) -> str:
    env_var = x.groups()[0]
    return os.environ.get(env_var, "")


def parse_env[T: NDict](args: T) -> T:
    """Replace dict values that looks 'env-like' with env variables."""
    def inner[TI: NDict](args: TI) -> TI:
        for i, value in args.items():
            match value:
                case dict():
                    args[i] = inner(value)
                case str():
                    args[i] = envsub.sub(_env_replace, value)
                case _:
                    msg = f"Found unhandled type {type(value)} in dict"
                    raise NotImplementedError(msg)
        return args

    return inner(args)
