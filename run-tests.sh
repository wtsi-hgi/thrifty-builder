#!/usr/bin/env bash

set -euf -o pipefail

# Remove old test coverage data
rm -f .coverage.*

# Run tests
PYTHONPATH=. python -m coverage run -m unittest discover -v -s thriftybuilder/tests
PYTHONPATH=. python -m coverage run thriftybuilder/cli.py -h
python -m coverage run setup.py -q install

# Generate coverage reports
coverage combine -a
coverage report
