"""
Defines the routes of a Flask webserver for namer.
"""
from loguru import logger
from pathlib import Path
from queue import Queue
from flask import Blueprint, jsonify, render_template, request
from flask.wrappers import Response

from namer.fileutils import analyze_relative_to
from namer.types import NamerConfig
from namer.web.actions import delete_file, get_failed_files, get_search_results


def get_web_routes(config: NamerConfig, command_queue: Queue) -> Blueprint:
    """
    Builds a blueprint for flask with passed in context, the NamerConfig.
    """
    blueprint = Blueprint('/', __name__, static_url_path='/', static_folder='public', template_folder='templates')
    command_queue = command_queue

    """
    @blueprint.route('/')
    def index() -> str:
         data = []
         for rule in app.url_map.iter_rules():
             if rule.methods is not None and 'GET' in rule.methods and has_no_empty_params(rule):
                 url = url_for(rule.endpoint, **(rule.defaults or {}))
                 data.append((url, rule.endpoint))

         return render_template('pages/index.html', links=data)
     """

    @blueprint.route('/')
    def failed() -> str:
        """
        Displays all failed to name files.
        """
        data = get_failed_files(config)
        return render_template('pages/failed.html', data=data, config=config)

    @blueprint.route('/api/v1/render', methods=['POST'])
    def render() -> Response:
        data = request.json

        res = False
        if data is not None:
            template = data.get('template')
            data = data.get('data')

            template_file = f'render/{template}.html'
            data = render_template(template_file, data=data, config=config)

            res = {
                'response': data,
            }

        return jsonify(res)

    @blueprint.route('/api/v1/get_files', methods=['POST'])
    def get_files() -> Response:
        data = get_failed_files(config)
        return jsonify(data)

    @blueprint.route('/api/v1/get_search', methods=['POST'])
    def get_results() -> Response:
        data = request.json

        res = False
        if data is not None:
            res = get_search_results(data['query'], data['file'], config)

        return jsonify(res)

    @blueprint.route('/api/v1/rename', methods=['POST'])
    def rename() -> Response:
        data = request.json

        res = False
        if data is not None:
            res = False
            if command_queue is not None:
                movie = config.failed_dir / Path(data['file'])
                logger.error(f"moving movie {movie}")
                command = analyze_relative_to(movie, config.failed_dir, config=config)
                if command is not None:
                    command.tpdbid = data['scene_id']
                    command_queue.put(command)  # Todo pass selection
        return jsonify(res)

    @blueprint.route('/api/v1/delete', methods=['POST'])
    def delete() -> Response:
        data = request.json

        res = False
        if data is not None:
            res = delete_file(data['file'], config)

        return jsonify(res)

    return blueprint
