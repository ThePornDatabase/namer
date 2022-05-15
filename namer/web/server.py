from typing import Any

from flask import Flask
from waitress import create_server

from namer.types import NamerConfig
from namer.web.routes import create_blueprint

app = Flask(__name__)


class WebServer:
    __server: Any  # MultiSocketServer | BaseWSGIServer
    __config: NamerConfig
    __debug: bool

    def __init__(self, config: NamerConfig, debug: bool = False):
        self.__config = config
        self.__debug = debug

        self.__make_server()

    def __make_server(self):
        path = '/' if self.__config.web_root is None else self.__config.web_root
        blueprint = create_blueprint(self.__config)
        app.register_blueprint(blueprint, url_prefix=path, root_path=path)

        if self.__debug:
            app.run(debug=True, host=self.__config.host, port=self.__config.port)
        else:
            self.__server = create_server(app, host=self.__config.host, port=self.__config.port)
            self.__server.run()

    def run(self):
        """
        Start server on existing thread.
        """
        self.__server.run()

    def stop(self):
        """
        Stop severing requests and empty threads.
        """
        self.__server.close()
