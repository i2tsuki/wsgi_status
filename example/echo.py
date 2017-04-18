import time


def app(environ, start_response):
    """Simplest possible application object"""

    time.sleep(1)

    if environ['REQUEST_METHOD'].upper() != 'POST':
        data = b'Hello, World!\n'
    else:
        data = environ['wsgi.input'].read()

    status = '200 OK'

    response_headers = [
        ('Content-type', 'text/plain'),
        ('Content-Length', str(len(data))),
    ]
    start_response(status, response_headers)
    return iter([data])
