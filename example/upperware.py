# -*- coding: utf-8 -*-

from wsgi_status import monitor

import echo

filename = "/dev/shm/gunicorn_stat.json"
app = monitor.Monitor(echo.app, filename)
