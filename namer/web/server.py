"""
A wrapper allowing shutdown of a Flask server.
"""
from typing import Any

from flask import Flask
from flask_compress import Compress
from waitress import create_server

from namer.types import NamerConfig
from namer.web.routes import get_web_routes

app = Flask(__name__)
compress = Compress()


class WebServer:
    """
    A wrapper allowing shutdown of a Flask server.
    """
    __server: Any  # MultiSocketServer | BaseWSGIServer
    __config: NamerConfig
    __debug: bool

    def __init__(self, config: NamerConfig, debug: bool = False):
        self.__config = config
        self.__debug = debug

        self.__make_server()

    def __make_server(self):
        path = '/' if self.__config.web_root is None else self.__config.web_root
        blueprint = get_web_routes(self.__config)
        app.register_blueprint(blueprint, url_prefix=path, root_path=path)
        if not self.__debug:
            compress.init_app(app)
            self.__server = create_server(app, host=self.__config.host, port=self.__config.port)

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
        self.__server.close()
