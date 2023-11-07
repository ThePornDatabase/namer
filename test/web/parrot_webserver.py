import time
from pathlib import Path
from threading import Thread
from typing import Any, Dict, Optional, Callable

from flask import Blueprint, make_response, request
from flask.wrappers import Response

from namer.web.server import GenericWebServer


def get_routes(responses: Dict[str, Any]) -> Blueprint:
    """
    Builds a blueprint for flask with passed in context, the NamerConfig.
    """
    blueprint = Blueprint('/', __name__)

    @blueprint.route('/', defaults={'path': ''})
    @blueprint.route('/<path:path>')
    def get_files(path) -> Response:
        # args = request.args
        output = responses.get(request.full_path)
        value = None
        if isinstance(output, Callable):
            output = output()
        if isinstance(output, bytearray):
            value = output
        if isinstance(output, Path):
            file: Path = output
            value = bytearray(file.read_bytes())
        if isinstance(output, str):
            value = bytearray(output, 'utf-8')

        if value:
            response = make_response(value, 200)
        else:
            response = make_response('', 404)
        # response.mimetype = "text/plain"
        return response

    return blueprint


class ParrotWebServer(GenericWebServer):
    __responses: Dict[str, Any]
    __background_thread: Optional[Thread]

    def __init__(self):
        self.__responses = {}
        super().__init__('127.0.0.1', port=0, webroot='/', blueprints=[get_routes(self.__responses)], static_path=None)

    def __enter__(self):
        self.__background_thread = Thread(target=self.start)
        self.__background_thread.start()

        tries = 0
        while super().get_effective_port() is None and tries < 20:
            time.sleep(0.2)
            tries += 1

        if super().get_effective_port is None:
            raise RuntimeError('application did not get assigned a port within 4 seconds.')

        return self

    def __simple_exit__(self):
        self.stop()
        if self.__background_thread is not None:
            self.__background_thread.join()
            del self.__background_thread

    def __exit__(self, exc_type, exc_value, traceback):
        self.__simple_exit__()

    def set_response(self, url: str, response):
        self.__responses[url] = response
