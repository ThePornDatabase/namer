import argparse
from cProfile import run
import sys
from typing import Optional

from flask import Flask, jsonify, render_template, request, url_for, Blueprint
from htmlmin.main import minify
from loguru import logger
from waitress import create_server
from waitress.server import MultiSocketServer, BaseWSGIServer

from namer.types import NamerConfig, default_config
from namer.web.helpers import get_files, get_search_results, has_no_empty_params, make_rename

app = Flask(__name__)
bp = Blueprint(name="/", import_name=__name__, static_url_path="/", static_folder='public', template_folder='templates')
config: NamerConfig

#@bp.route('/')
#def index():
#    data = []
#    for rule in app.url_map.iter_rules():
#        if rule.methods is not None and 'GET' in rule.methods and has_no_empty_params(rule):
#            url = url_for(rule.endpoint, **(rule.defaults or {}))
#            data.append((url, rule.endpoint))
#
#    return render_template('pages/index.html', links=data)


class RunAndStoppable:

    server: MultiSocketServer | BaseWSGIServer

    def __init__(self, server: MultiSocketServer | BaseWSGIServer):
        self.server = server

    def run(self):
        self.server.run()

    def stop(self):
        self.server.close()


@bp.route('/')
def files():
    data = get_files(config)
    return render_template('pages/failed.html', files=data)


@bp.route('/render', methods=['POST'])
def render():
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


@bp.route('/get_search', methods=['POST'])
def get_results():
    data = request.json
    if data is not None:
        res = get_search_results(data['query'], data['file'], config)
        return jsonify(res)


@bp.route('/rename', methods=['POST'])
def rename():
    data = request.json
    if data is not None:
        res = make_rename(data['file'], data['scene_id'], config)
        return jsonify(res)


@bp.after_request
def response_minify(response):
    if 'text/html' in response.content_type:
        response.set_data(minify(response.get_data(as_text=True)))

        return response

    return response


def start_server(namer_config: NamerConfig, debug: bool = False) -> RunAndStoppable:
    global config
    config = namer_config
    path="/" if config.web_root is None else config.web_root
    app.register_blueprint(bp, url_prefix=path, root_path=path)
    server = create_server(app, host=config.host, port=config.port)
    return RunAndStoppable(server)

def debug_server(namer_config: NamerConfig, debug: bool = False):
    global config
    config = namer_config
    path="/" if config.web_root is None else config.web_root
    app.register_blueprint(bp, url_prefix=path, root_path=path)
    app.run(debug=True, host=config.host, port=config.port)

def main(arg_list: list[str]):
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
        debug_server(local_config, args.debug)
    else:
        start_server(local_config, args.debug).run()


if __name__ == '__main__':
    main(sys.argv[1:])
