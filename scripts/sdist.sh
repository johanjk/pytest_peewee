#!/usr/bin/env bash
set -e
cd "$(dirname "$(realpath "$0")")" && cd ..

uv build
mkdir -p dist/sdist
tar xvzf dist/*.tar.gz  -C dist/sdist --strip-components=1
(
    cd dist/sdist
    # exit existing env
    unset VIRTUAL_ENV
    unset VIRTUAL_ENV_PROMPT
    uv run poe ci
)
rm -rf dist/sdist
