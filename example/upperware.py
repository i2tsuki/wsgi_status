# -*- coding: utf-8 -*-

from wsgi_status.monitor import Monitor

import echo

filename = "/dev/shm/gunicorn_stat.json"
app = Monitor(echo.app, filename)
