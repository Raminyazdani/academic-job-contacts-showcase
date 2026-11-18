"""Run a temporary HTTP listener on an OS-assigned loopback port."""

from contextlib import contextmanager
from socket import AF_INET, SOCK_STREAM, socket
from threading import Thread
from time import monotonic, sleep

import uvicorn


@contextmanager
def local_server(app):
    with socket(AF_INET, SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        config = uvicorn.Config(app, log_level="error", access_log=False)
        server = uvicorn.Server(config)
        worker = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        try:
            deadline = monotonic() + 10
            while not server.started:
                if not worker.is_alive() or monotonic() >= deadline:
                    raise RuntimeError("The local HTTP server could not start")
                sleep(0.01)
            yield f"http://127.0.0.1:{port}"
        finally:
            server.should_exit = True
            worker.join(timeout=10)
            if worker.is_alive():
                raise RuntimeError("The local HTTP server could not stop")
