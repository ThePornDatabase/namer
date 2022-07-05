"""
A wrapper allowing shutdown of a Flask server.
"""
import mimetypes
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
    __command_queue: Queue

    __mime_types: dict = {
        'font/woff': '.woff',
        'font/woff2': '.woff2',
    }

    def __init__(self, config: NamerConfig, command_queue: Queue):
        self.__config = config
        self.__command_queue = command_queue
        self.__add_mime_types()
        self.__make_server()

    def __make_server(self):
        path = '/' if self.__config.web_root is None else self.__config.web_root
        blueprint = get_web_routes(self.__config, self.__command_queue)
        app.register_blueprint(blueprint, url_prefix=path, root_path=path)
        compress.init_app(app)
        self.__server = create_server(app, host=self.__config.host, port=self.__config.port)
        self.__thread = Thread(target=self.__run, daemon=True)

    def __add_mime_types(self):
        app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'

        for mime, ext in self.__mime_types.items():
            test_mime, test_ext = mimetypes.guess_type(f'0{ext}')
            if test_mime is None:
                mimetypes.add_type(mime, ext)

    def start(self):
        self.__thread.start()

    def __run(self):
        """
        Start server on existing thread.
        """
        if self.__server:
            self.__server.run()

    def stop(self):
        """
        Stop severing requests and empty threads.
        """
        if self.__server:
            self.__server.close()

    def get_effective_port(self) -> Optional[int]:
        return getattr(self.__server, "effective_port", None)
