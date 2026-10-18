#!/usr/bin/env bash
set -e
cd "$(dirname "$(realpath "$0")")" && cd ..

# based on: https://pydistcheck.readthedocs.io/en/latest/how-to-test-a-python-distribution.html#quickstart

uv build
gunzip -tv dist/*.tar.gz
zip -T dist/*.whl
pyroma --min=10 dist/*.tar.gz
twine check --strict dist/*
pkginfo --json dist/*.tar.gz
pkginfo --json dist/*.whl
wheel2json dist/*.whl
check-wheel-contents dist/*.whl
pydistcheck --inspect dist/*.whl --expected-files '!*/tests' --expected-files '!*/src'
pydistcheck --inspect dist/*.tar.gz --expected-files '*/.gitignore' --expected-files '*/src/tests/*.py' --expected-files '*/src/*.py'
unzip -l dist/*.whl
tar -tf dist/*.tar.gz
