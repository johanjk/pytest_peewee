import os
import re

REGEX = r"\$([A-Z_][A-Z0-9_]+)"
envsub = re.compile(REGEX)


def _env_replace(x: re.Match) -> str:
    env_var = x.groups()[0]
    return os.environ.get(env_var, "")


def parse_env(args: dict) -> dict:
    def inner(args):
        for i, value in args.items():
            if isinstance(value, dict):
                args[i] = inner(value)
            elif isinstance(value, str):
                args[i] = envsub.sub(_env_replace, value)
        return args

    return inner(args)
