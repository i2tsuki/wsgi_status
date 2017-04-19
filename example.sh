#!/bin/sh

set -eu

python -m venv ./venv
./venv/bin/pip install -r ./requirements_test.txt
./venv/bin/python ./setup.py develop

cd ./examples
../venv/bin/gunicorn -c gunicorn.conf.py upperware:app
cd ${OLDPWD}
