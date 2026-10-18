#!/usr/bin/env bash
set -e
cd "$(dirname "$(realpath "$0")")" && cd ..

uv build
uv venv --clear "$1"
VIRTUAL_ENV="$1" uv pip install dist/*"$2"
"$1"/bin/python -c 'import pytest_peewee'
rm -r "$1"
