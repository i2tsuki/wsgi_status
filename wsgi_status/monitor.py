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
        self.worker = {
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
        self.update_status(init=True)

    def __call__(self, environ, start_response):
        if self.thread is True:
            resp = self.app(environ, start_response)
            return resp

        self.pre_request(environ)

        def post_request(status_code, headers, exc_info=None):
            self.worker["status"] = "idle"
            self.worker["uri"] = ""
            self.worker["method"] = ""
            self.update_status(init=False)
            return start_response(status_code, headers, exc_info)

        return self.app(environ, post_request)

    def pre_request(self, environ):
        self.worker["requests"] += 1
        self.worker["status"] = "busy"
        self.worker["uri"] = environ["PATH_INFO"]
        self.worker["method"] = environ["REQUEST_METHOD"]
        self.update_status(init=False)

    def handler(self, signum, stack):
        self.worker["status"] = str(signum)
        self.worker["uri"] = ""
        self.worker["method"] = ""

        proc = psutil.Process()
        files = proc.open_files()
        for f in files:
            if f.path == self.filename:
                fcntl.flock(f.fd, fcntl.LOCK_UN)
            self.update_status(init=False)
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

    def update_status(self, init):
        with open(self.filename, mode="r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                obj = {}
                try:
                    obj = json.load(f)
                except ValueError:
                    # Failed to json parse
                    obj = {
                        "workers": [],
                    }
                workers = [(i, v) for i, v in enumerate(obj["workers"]) if v["pid"] == self.pid]
                if len(workers) == 1:
                    index = workers[0][0]
                    obj["workers"][index] = self.worker
                else:
                    obj["workers"].append(self.worker)
                    if not init:
                        sys.stderr.write("not find self.pid: {} in workers key".format(self.pid))
                f.seek(0)
                f.truncate(0)
                json.dump(obj, f)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
