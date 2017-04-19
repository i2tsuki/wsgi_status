#!/bin/sh

set -eu

python -m venv ./venv
./venv/bin/python ./setup.py develop

cd ./examples
./venv/bin/gunicorn -c gunicorn.conf.py upperware:app
cd ${OLDPWD}
