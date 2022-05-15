from typing import Any, Optional

from flask import Blueprint, jsonify, render_template, request
from flask.wrappers import Response
from htmlmin.main import minify

from namer.types import NamerConfig
from namer.web.helpers import get_failed_files, get_search_results, make_rename


def create_blueprint(config: NamerConfig) -> Blueprint:
    """
    Builds a blueprint for flask with passed in context, the NamerConfig.
    """

    blueprint = Blueprint('/', __name__, static_url_path='/', static_folder='public', template_folder='templates')

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
    def index():
        """
        Displays all failed to name files.
        """
        data = get_failed_files(config)
        return render_template('pages/failed.html', data=data)

    @blueprint.route('/render', methods=['POST'])
    def render() -> Optional[Response]:
        data = request.json
        if data is not None:
            template = data.get('template')
            data = data.get('data')

            template_file = f'render/{template}.html'
            data = render_template(template_file, data=data)

            res = {
                'response': minify(data),
            }
            return jsonify(res)

    @blueprint.route('/get_files', methods=['POST'])
    def get_files() -> Optional[Response]:
        data = get_failed_files(config)
        return jsonify(data)

    @blueprint.route('/get_search', methods=['POST'])
    def get_results() -> Optional[Response]:
        data = request.json
        if data is not None:
            res = get_search_results(data['query'], data['file'], config)
            return jsonify(res)

    @blueprint.route('/rename', methods=['POST'])
    def rename() -> Optional[Response]:
        data = request.json
        if data is not None:
            res = make_rename(data['file'], data['scene_id'], config)
            return jsonify(res)

    @blueprint.after_request
    def response_minify(response: Any) -> Optional[Response]:
        if response is not None and 'text/html' in response.content_type:
            response.set_data(minify(response.get_data(as_text=True)))
            return response

        return response

    return blueprint
