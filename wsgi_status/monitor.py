# -*- coding: utf-8 -*-
import fcntl
import json
import os
import psutil
import stat
import signal
import sys
import time
import threading


class Monitor:
    def __init__(self, app, filename):
        self.app = app
        self.pid = os.getpid()
        self.filename = filename
        self.thread = False

        if self.is_threadmodel():
            self.thread = True
            with open(filename, mode="w") as fp:
                fp.write("{}{}".format(
                    "WSGI status does not support worker thread model.  ",
                    "Work only worker pre-fork."))
                return

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
                    "workers": [],
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
        worker = {
            "pid": self.pid,
            "requests": 0,
            "status": "idle",
            # "vss": 0,
            # "rss": 0,
            "last_spawn": int(time.time()),
            # "tx": 0,
            # "avg_rt": 0,
            "uri": "",
            "method": "",
        }
        with open(filename, mode="r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                obj = json.load(f)

                stats = [(i, v) for i, v in enumerate(obj["workers"]) if v["pid"] == self.pid]
                if len(stats) == 0:
                    obj["workers"].append(worker)
                else:
                    for i, _ in stats:
                        obj["workers"][i] = worker
                f.seek(0)
                f.truncate(0)
                json.dump(obj, f)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def __call__(self, environ, start_response):
        if self.thread is True:
            resp = self.app(environ, start_response)
            return resp

        self.pre_request(environ)

        def post_request(status_code, headers, exc_info=None):
            with open(self.filename, mode="r+") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    obj = json.load(f)

                    workers = [(i, v) for i, v in enumerate(obj["workers"]) if v["pid"] == self.pid]
                    if len(workers) != 1:
                        sys.stderr.write("not find self.pid: %d in workers key", self.pid)
                    index = workers[0][0]
                    worker = workers[0][1]
                    worker["status"] = "idle"
                    worker["uri"] = ""
                    worker["method"] = ""
                    obj["workers"][index] = worker

                    f.seek(0)
                    f.truncate(0)
                    json.dump(obj, f)
                    f.flush()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return start_response(status_code, headers, exc_info)

        return self.app(environ, post_request)

    def pre_request(self, environ):
        with open(self.filename, mode="r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                obj = json.load(f)

                workers = [(i, v) for i, v in enumerate(obj["workers"]) if v["pid"] == self.pid]
                if len(workers) != 1:
                    sys.stderr.write("not find self.pid: %d in workers key", self.pid)

                index = workers[0][0]
                worker = workers[0][1]
                worker["requests"] += 1
                worker["status"] = "busy"
                worker["uri"] = environ["PATH_INFO"]
                worker["method"] = environ["REQUEST_METHOD"]
                obj["workers"][index] = worker

                f.seek(0)
                f.truncate(0)
                json.dump(obj, f)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def handler(self, signum, stack):
        with open(self.filename, mode="r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                obj = json.load(f)

                workers = [(i, v) for i, v in enumerate(obj["workers"]) if v["pid"] == self.pid]
                if len(workers) != 1:
                    sys.stderr.write("not find self.pid: %d in workers key", self.pid)
                index = workers[0][0]
                worker = workers[0][1]
                worker["status"] = str(signum)
                worker["uri"] = ""
                worker["method"] = ""
                obj["workers"][index] = worker

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

    def is_threadmodel(self):
        if threading.active_count() > 1:
            return True
        return False

    def status(self, environ, start_response):
        status = '200 OK'

        with open(self.filename, mode="r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                obj = json.load(f)
                for i, worker in enumerate(obj["workers"]):
                    # Catch exception when the process is terminated by master
                    try:
                        process = psutil.Process(worker["pid"])
                        vms = process.memory_info().vms
                        obj["workers"][i]["vss"] = vms
                        rss = process.memory_info().rss
                        obj["workers"][i]["rss"] = rss
                    except:
                        pass
                data = json.dumps(obj).encode(encoding="utf-8")
                response_headers = [
                    ('Content-type', 'application/json'),
                    ('Content-Length', str(len(data))),
                ]
                start_response(status, response_headers)

            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return iter([data])
