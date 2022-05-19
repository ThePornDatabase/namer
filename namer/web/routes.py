"""
Defines the routes of a Flask webserver for namer.
"""
from flask import Blueprint, jsonify, render_template, request
from flask.wrappers import Response

from namer.types import NamerConfig
from namer.web.helpers import delete_file, get_failed_files, get_search_results, make_rename


def get_web_routes(config: NamerConfig) -> Blueprint:
    """
    Builds a blueprint for flask with passed in context, the NamerConfig.
    """

    blueprint = Blueprint('/', __name__, static_url_path='/', static_folder='public', template_folder='templates')

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
        return render_template('pages/failed.html', data=data)

    @blueprint.route('/api/v1/render', methods=['POST'])
    def render() -> Response:
        data = request.json

        res = False
        if data is not None:
            template = data.get('template')
            data = data.get('data')

            template_file = f'render/{template}.html'
            data = render_template(template_file, data=data)

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
            res = make_rename(data['file'], data['scene_id'], config)

        return jsonify(res)

    @blueprint.route('/api/v1/delete', methods=['POST'])
    def delete() -> Response:
        data = request.json

        res = False
        if data is not None:
            res = delete_file(data['file'], config)

        return jsonify(res)

    return blueprint
