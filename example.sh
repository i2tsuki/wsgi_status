#!/bin/sh

exec 2>&1

set -eu

python -m venv ./venv
./venv/bin/python ./setup.py develop

./venv/bin/pip install gunicorn
cd ./examples
../venv/bin/gunicorn -c gunicorn.conf.py upperware:app
cd ${OLDPWD}
