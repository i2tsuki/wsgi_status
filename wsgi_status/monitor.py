# -*- coding: utf-8 -*-
import fcntl
import json
import os
import psutil
import stat
import signal
import sys
import threading


class Monitor:
    def __init__(self, app, filename):
        if self.is_threading():
            sys.stderr.write("does not support worker threading model.  use only worker pre-fork")
            sys.exit(1)

        self.wrapped_app = app
        self.pid = os.getpid()
        self.filename = filename

        self.pre_sigint_handler = signal.getsignal(signal.SIGINT)
        self.pre_sigterm_handler = signal.getsignal(signal.SIGTERM)
        self.pre_sigabrt_handler = signal.getsignal(signal.SIGABRT)

        # Create status file for own process permissions
        ppid_ctime = psutil.Process(os.getppid()).create_time()
        file_ctime = 0.0
        if os.path.exists(self.filename):
            file_ctime = os.stat(self.filename).st_ctime
            if ppid_ctime > file_ctime:
                os.remove(self.filename)
        if ppid_ctime > file_ctime:
            with open(filename, mode="w") as f:
                obj = {
                    "TotalAccesses": 0,
                    "IdleWorkers": 0,
                    "BusyWorkers": 0,
                    "stats": [],
                }
                json.dump(obj, f)
                os.chown(filename, os.getuid(), os.getgid())
                statinfo = os.stat(filename)
                mode = statinfo.st_mode + stat.S_IWGRP
                os.chmod(filename, mode=mode)

        # Handler for receiving termination signal
        signal.signal(signal.SIGINT, self.handler)
        signal.signal(signal.SIGTERM, self.handler)
        signal.signal(signal.SIGABRT, self.handler)

        # Update an initial process status in status file
        status = {
            "pid": self.pid,
            "host": "",
            "method": "",
            "uri": "",
            "status": "_"
        }
        with open(filename, mode="r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                obj = json.load(f)

                stats = [(i, v) for i, v in enumerate(obj["stats"]) if v["pid"] == self.pid]
                if len(stats) == 0:
                    obj["stats"].append(status)
                else:
                    for i, _ in stats:
                        obj["stats"][i] = status
                obj["IdleWorkers"] = obj["IdleWorkers"] + 1

                f.seek(0)
                f.truncate(0)
                json.dump(obj, f)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def __call__(self, environ, start_response):
        if environ["REMOTE_ADDR"] == "127.0.0.1":
            if environ["PATH_INFO"] == "/wsgi_status":
                return self.status(environ, start_response)
        self.pre_request(environ)
        resp = self.wrapped_app(environ, start_response)
        self.post_request(environ)
        return resp

    def pre_request(self, environ):
        status = {
            "pid": self.pid,
            "host": environ["HTTP_HOST"],
            "method": environ["REQUEST_METHOD"],
            "uri": environ["PATH_INFO"],
            "status": "A"
        }

        with open(self.filename, mode="r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                obj = json.load(f)

                stats = [(i, v) for i, v in enumerate(obj["stats"]) if v["pid"] == self.pid]
                if len(stats) == 0:
                    # ("not find self.pid: %d in stats object", self.pid)
                    pass
                else:
                    for i, _ in stats:
                        obj["stats"][i] = status

                obj["TotalAccesses"] = obj["TotalAccesses"] + 1
                obj["IdleWorkers"] = obj["IdleWorkers"] - 1
                obj["BusyWorkers"] = obj["BusyWorkers"] + 1

                f.seek(0)
                f.truncate(0)
                json.dump(obj, f)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def post_request(self, environ):
        status = {
            "pid": self.pid,
            "host": environ["HTTP_HOST"],
            "method": environ["REQUEST_METHOD"],
            "uri": environ["PATH_INFO"],
            "status": "_"
        }
        with open(self.filename, mode="r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                obj = json.load(f)

                stats = [(i, v) for i, v in enumerate(obj["stats"]) if v["pid"] == self.pid]
                if len(stats) == 0:
                    # ("not find self.pid: %d in stats object", self.pid)
                    pass
                else:
                    for i, _ in stats:
                        obj["stats"][i] = status

                obj["IdleWorkers"] = obj["IdleWorkers"] + 1
                obj["BusyWorkers"] = obj["BusyWorkers"] - 1

                f.seek(0)
                f.truncate(0)
                json.dump(obj, f)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def handler(self, signum, stack):
        status = {
            "pid": self.pid,
            "host": "",
            "method": "",
            "uri": "",
            "status": str(signum),
        }

        with open(self.filename, mode="r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                obj = json.load(f)

                stats = [(i, v) for i, v in enumerate(obj["stats"]) if v["pid"] == self.pid]
                if len(stats) == 0:
                    obj["stats"].append(status)
                else:
                    for i, v in stats:
                        if v["status"] == "A":
                            obj["BusyWorkers"] = obj["BusyWorkers"] - 1
                        else:
                            obj["IdleWorkers"] = obj["IdleWorkers"] - 1
                        status["host"] = v["host"]
                        status["method"] = v["method"]
                        status["uri"] = v["uri"]
                        obj["stats"][i] = status

                f.seek(0)
                f.truncate(0)
                json.dump(obj, f)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            if signum == signal.SIGINT:
                self.pre_sigint_handler(signum, stack)
            elif signum == signal.SIGTERM:
                self.pre_sigterm_handler(signum, stack)
            elif signum == signal.SIGABRT:
                self.pre_sigabrt_handler(signum, stack)
            sys.exit(1)

    def is_threading(self):
        if threading.active_count() > 1:
            return True
        return False

    def status(self, environ, start_response):
        status = '200 OK'

        with open(self.filename, mode="rb") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = f.read()
                response_headers = [
                    ('Content-type', 'application/json'),
                    ('Content-Length', str(len(data))),
                ]
                start_response(status, response_headers)

            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return iter([data])
