#!/bin/sh

set -eu

python -m venv ./venv
./venv/bin/pip install -U -r ./requirements_example.txt
./venv/bin/gunicorn -c gunicorn.conf.py upperware:app
