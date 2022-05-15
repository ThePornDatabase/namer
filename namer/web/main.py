"""
Creates a webserver allowing the renaming of failed files.
"""

import argparse
import sys
from typing import Any, Optional

from flask import Flask, jsonify, render_template, request, Blueprint
from flask.wrappers import Response
from htmlmin.main import minify
from loguru import logger
from waitress import create_server
from waitress.server import MultiSocketServer, BaseWSGIServer

from namer.types import NamerConfig, default_config
from namer.web.helpers import get_files, get_search_results, make_rename

app = Flask(__name__)


class RunAndStoppable:
    """
    Has a stop method to allow for halting the webserver.
    """

    server: MultiSocketServer | BaseWSGIServer

    def __init__(self, server: MultiSocketServer | BaseWSGIServer):
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


def create_blueprint(config: NamerConfig) -> Blueprint:
    """
    Builds a blueprint for flask with passed in context, the NamerConfig.
    """

    blueprint = Blueprint("/", __name__, static_url_path="/", static_folder='public', template_folder='templates')

    # @blueprint.route('/')
    # def index():
    #     data = []
    #     for rule in app.url_map.iter_rules():
    #         if rule.methods is not None and 'GET' in rule.methods and has_no_empty_params(rule):
    #             url = url_for(rule.endpoint, **(rule.defaults or {}))
    #             data.append((url, rule.endpoint))
    #
    #     return render_template('pages/index.html', links=data)

    @blueprint.route('/')
    def files():
        """
        Displays all failed to name files.
        """
        data = get_files(config)
        return render_template('pages/failed.html', files=data)

    @blueprint.route('/render', methods=['POST'])
    def render() -> Optional[Response]:
        data = request.json
        if data is not None:
            template = data.get('template')
            data = data.get('data')

            template_file = f'components/{template}.html'
            data = render_template(template_file, data=data)

            res = {
                'response': minify(data),
            }
            return jsonify(res)
        return None

    @blueprint.route('/get_search', methods=['POST'])
    def get_results() -> Optional[Response]:
        data = request.json
        if data is not None:
            res = get_search_results(data['query'], data['file'], config)
            return jsonify(res)
        return None

    @blueprint.route('/rename', methods=['POST'])
    def rename() -> Optional[Response]:
        data = request.json
        if data is not None:
            res = make_rename(data['file'], data['scene_id'], config)
            return jsonify(res)
        return None

    @blueprint.after_request
    def response_minify(response: Any) -> Response:
        if response is not None and 'text/html' in response.content_type:
            response.set_data(minify(response.get_data(as_text=True)))
            return response
        return response

    return blueprint


def start_server(config: NamerConfig) -> RunAndStoppable:
    """
    starts a web server with config from NamerConfig.
    """
    path = "/" if config.web_root is None else config.web_root
    blueprint = create_blueprint(config)
    app.register_blueprint(blueprint, url_prefix=path, root_path=path)
    server = create_server(app, host=config.host, port=config.port)
    return RunAndStoppable(server)


def debug_server(config: NamerConfig):
    """
    starts a web server with config from NamerConfig in debug mode.
    """
    path = "/" if config.web_root is None else config.web_root
    blueprint = create_blueprint(config)
    app.register_blueprint(blueprint, url_prefix=path, root_path=path)
    app.run(debug=True, host=config.host, port=config.port)


def main(arg_list: list[str]):
    """
    uses default namer config, with possible override port and host, and potentially in debug mode.
    """
    local_config = default_config()
    parser = argparse.ArgumentParser(description='Namer webserver')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--host', type=str, help='Server host')
    parser.add_argument('-p', '--port', type=int, help='Server port')
    args = parser.parse_args(arg_list)
    local_config.web = True
    if args.host is not None:
        local_config.host = args.host
    if args.port is not None:
        local_config.port = args.port
    level = "DEBUG" if args.debug else "ERROR"
    logger.remove()
    logger.add(sys.stdout, format="{time} {level} {message}", level=level)
    if args.debug:
        debug_server(local_config)
    else:
        start_server(local_config).run()


if __name__ == '__main__':
    main(sys.argv[1:])
