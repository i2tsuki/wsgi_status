WSGI-status
-----------

WSGI-status is a Python WSGI Middleware for monitoring WSGI application.
It records worker status and provide worker status as a file.
WSGI-status is inspired by uWSGI ``--stats`` option.
These metrics that uWSGI provide are not given by other WSGI server middleware such as Gunicorn.
WSGI-status provide worker metrics like uWSGI format.

Usage
-----

Examples echo.py with Gunicorn::

    $ ./example.sh

And see ``examples/upperware.py`` directory.

License
-------

WSGI-status is released under the MIT License. See the LICENSE file for more details.
