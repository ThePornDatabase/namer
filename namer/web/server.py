"""
A wrapper allowing shutdown of a Flask server.
"""
from queue import Queue
from threading import Thread
from typing import Optional, Union

from flask import Flask
from flask_compress import Compress
from waitress import create_server
from waitress.server import BaseWSGIServer, MultiSocketServer

from namer.types import NamerConfig
from namer.web.routes import get_web_routes

app = Flask(__name__)
compress = Compress()


class WebServer:
    """
    A wrapper allowing shutdown of a Flask server.
    """
    __server: Union[MultiSocketServer, BaseWSGIServer]
    __thread: Thread
    __config: NamerConfig
    __debug: bool
    __command_queue: Queue

    def __init__(self, config: NamerConfig, command_queue: Queue, debug: bool = False):
        self.__config = config
        self.__debug = debug
        self.__command_queue = command_queue
        self.__make_server()

    def __make_server(self):
        path = '/' if self.__config.web_root is None else self.__config.web_root
        blueprint = get_web_routes(self.__config, self.__command_queue)
        app.register_blueprint(blueprint, url_prefix=path, root_path=path)
        if not self.__debug:
            compress.init_app(app)
            self.__server = create_server(app, host=self.__config.host, port=self.__config.port)
            self.__thread = Thread(target=self.run, daemon=True)

    def start(self):
        self.__thread.start()

    def run(self):
        """
        Start server on existing thread.
        """
        if self.__debug:
            app.run(debug=True, host=self.__config.host, port=self.__config.port)
        else:
            self.__server.run()

    def stop(self):
        """
        Stop severing requests and empty threads.
        """
        if self.__server:
            self.__server.close()

    def get_effective_port(self) -> Optional[int]:
        port = None
        if hasattr(self.__server, "effective_port"):
            port = self.__server.effective_port  # type: ignore
        return port
