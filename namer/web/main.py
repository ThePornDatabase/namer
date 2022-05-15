"""
Creates a webserver allowing the renaming of failed files.
"""

import argparse
import sys
from typing import Any, List

from flask import Flask
from loguru import logger
from waitress import create_server

from namer.types import default_config, NamerConfig
from namer.web.routes import create_blueprint

app = Flask(__name__)


class RunAndStoppable:
    """
    Has a stop method to allow for halting the webserver.
    """

    server: Any  # MultiSocketServer | BaseWSGIServer

    def __init__(self, server: Any):
        self.server = server

    def run(self):
        """
        Start server on existing thread.
        """
        self.server.run()

    def stop(self):
        """
        Stop severing requests and empty threads.
        """
        self.server.close()


def start_server(config: NamerConfig) -> RunAndStoppable:
    """
    starts a web server with config from NamerConfig.
    """
    path = '/' if config.web_root is None else config.web_root
    blueprint = create_blueprint(config)
    app.register_blueprint(blueprint, url_prefix=path, root_path=path)
    server = create_server(app, host=config.host, port=config.port)
    return RunAndStoppable(server)


def debug_server(config: NamerConfig):
    """
    starts a web server with config from NamerConfig in debug mode.
    """
    path = '/' if config.web_root is None else config.web_root
    blueprint = create_blueprint(config)
    app.register_blueprint(blueprint, url_prefix=path, root_path=path)
    app.run(debug=True, host=config.host, port=config.port)


def main(arg_list: List[str]):
    """
    uses default namer config, with possible override port and host, and potentially in debug mode.
    """
    parser = argparse.ArgumentParser(description='Namer webserver')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--host', type=str, help='Server host')
    parser.add_argument('-p', '--port', type=int, help='Server port')
    args = parser.parse_args(arg_list)

    local_config = default_config()
    local_config.web = True
    if args.host is not None:
        local_config.host = args.host
    if args.port is not None:
        local_config.port = args.port

    level = 'DEBUG' if args.debug else 'ERROR'
    logger.remove()
    logger.add(sys.stdout, format="{time} {level} {message}", level=level)

    if args.debug:
        debug_server(local_config)
    else:
        start_server(local_config).run()


if __name__ == '__main__':
    main(sys.argv[1:])
