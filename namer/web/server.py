"""
A wrapper allowing shutdown of a Flask server.
"""
import mimetypes
from threading import Thread
from typing import List, Optional, Union

from flask import Flask, Blueprint
from flask_compress import Compress
from waitress import create_server
from waitress.server import BaseWSGIServer, MultiSocketServer


class WebServer:
    """
    A wrapper allowing shutdown of a Flask server.
    """
    __app: Flask
    __compress = Compress()

    __path: str
    __port: int
    __host: str
    __webroot: Optional[str]
    __blueprints: List[Blueprint]

    __server: Union[MultiSocketServer, BaseWSGIServer]
    __thread: Thread

    __mime_types: dict = {
        'font/woff': '.woff',
        'font/woff2': '.woff2',
    }

    def __init__(self, host: str, port: int, webroot: Optional[str], blueprints: List[Blueprint]):
        self.__host = host
        self.__port = port
        self.__webroot = webroot
        self.__path = '/' if not self.__webroot else self.__webroot
        self.__app = Flask(__name__, static_url_path=self.__path, static_folder='public', template_folder='templates')
        self.__blueprints = blueprints

        self.__add_mime_types()
        self.__register_blueprints()
        self.__make_server()

    def __make_server(self):
        self.__compress.init_app(self.__app)
        self.__server = create_server(self.__app, host=self.__host, port=self.__port)
        self.__thread = Thread(target=self.__run, daemon=True)

    def __register_blueprints(self):
        for blueprint in self.__blueprints:
            blueprint_path = self.__path + blueprint.url_prefix if blueprint.url_prefix else self.__path
            self.__app.register_blueprint(blueprint, url_prefix=blueprint_path)

    def __add_mime_types(self):
        self.__app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'

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
