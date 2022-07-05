"""
Defines the web routes of a Flask webserver for namer.
"""
from queue import Queue

from flask import Blueprint, redirect, render_template
from flask.wrappers import Response

from namer.types import NamerConfig
from namer.web.actions import get_failed_files, get_queued_files


def get_web_routes(config: NamerConfig, command_queue: Queue) -> Blueprint:
    """
    Builds a blueprint for flask with passed in context, the NamerConfig.
    """
    blueprint = Blueprint('web', __name__, static_url_path='/', static_folder='public', template_folder='templates')

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
    def index() -> Response:
        return redirect('/failed', code=302)

    @blueprint.route('/failed')
    def failed() -> str:
        """
        Displays all failed to name files.
        """
        data = get_failed_files(config)
        return render_template('pages/failed.html', data=data, config=config)

    @blueprint.route('/queue')
    def queue() -> str:
        """
        Displays all queued files.
        """
        data = get_queued_files(command_queue)
        return render_template('pages/queue.html', data=data, config=config)

    return blueprint
