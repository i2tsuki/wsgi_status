#!/bin/sh

set -eu

python -m venv ./venv
./venv/bin/pip install -r ./requirements.txt
