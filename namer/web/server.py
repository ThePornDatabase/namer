"""
A wrapper allowing shutdown of a Flask server.
"""

import datetime
import logging
import mimetypes
from queue import Queue
from threading import Thread
from typing import Any, List, Optional, Union

import numpy
import orjson
from flask import Blueprint, Flask
from flask.json.provider import _default, JSONProvider
from flask_compress import Compress
from loguru import logger
from waitress import create_server
from waitress.server import BaseWSGIServer, MultiSocketServer
from werkzeug.middleware.proxy_fix import ProxyFix

from namer.configuration import NamerConfig
from namer.configuration_utils import from_str_list_lower
from namer.videophash import ImageHash
from namer.web.routes import api, web


class GenericWebServer:
    """
    A wrapper allowing shutdown of a Flask server.
    """

    __app: Flask
    __compress = Compress()

    __port: int
    __host: str
    __path: str
    __blueprints: List[Blueprint]

    __server: Union[MultiSocketServer, BaseWSGIServer]
    __thread: Thread

    __mime_types: dict = {
        'font/woff': '.woff',
        'font/woff2': '.woff2',
    }

    def __init__(self, host: str, port: int, webroot: Optional[str], blueprints: List[Blueprint], static_path: Optional[str] = 'public', quiet=True):
        self.__host = host
        self.__port = port
        self.__path = webroot if webroot else '/'
        self.__app = Flask(__name__, static_url_path=self.__path, static_folder=static_path, template_folder='templates')
        self.__blueprints = blueprints

        if quiet:
            logging.getLogger('waitress').disabled = True
            logging.getLogger('waitress.queue').disabled = True

        self.__add_mime_types()
        self.__register_blueprints()
        self.__make_server()
        self.__register_custom_processors()

    def __make_server(self):
        self.__app.wsgi_app = ProxyFix(self.__app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        self.__compress.init_app(self.__app)
        self.__server = create_server(self.__app, host=self.__host, port=self.__port, clear_untrusted_proxy_headers=True)
        self.__thread = Thread(target=self.__run, daemon=True)

    def __register_blueprints(self):
        for blueprint in self.__blueprints:
            blueprint_path = self.__path + blueprint.url_prefix if blueprint.url_prefix else self.__path
            self.__app.register_blueprint(blueprint, url_prefix=blueprint_path)

    def __add_mime_types(self):
        self.__app.json.mimetype = 'application/json; charset=utf-8'  # type: ignore

        for mime, ext in self.__mime_types.items():
            test_mime, test_ext = mimetypes.guess_type(f'0{ext}')
            if test_mime is None:
                mimetypes.add_type(mime, ext)

    def __register_custom_processors(self):
        functions = {
            'bool_to_icon': self.bool_to_icon,
        }
        self.__app.jinja_env.globals.update(**functions)

        filters = {
            'timestamp_to_datetime': self.timestamp_to_datetime,
            'seconds_to_format': self.seconds_to_format,
            'strftime': self.strftime,
            'is_list': self.is_list,
            'is_dict': self.is_dict,
            'from_list': from_str_list_lower,
        }
        self.__app.jinja_env.filters.update(**filters)

        self.__app.jinja_env.add_extension('jinja2.ext.do')

        self.__app.jinja_env.trim_blocks = True
        self.__app.jinja_env.lstrip_blocks = True

        self.__app.json = CustomJSONProvider(self.__app)

    def start(self):
        logger.info(f'Starting server: {self.get_url()}')
        self.__thread.start()

    def __run(self):
        """
        Start server on existing thread.
        """
        if self.__server:
            try:
                self.__server.run()
            except OSError:
                logger.error('Stopping server')
            finally:
                self.stop()

    def stop(self):
        """
        Stop severing requests and empty threads.
        """
        if self.__server:
            self.__server.close()

    def get_effective_port(self) -> Optional[int]:
        return getattr(self.__server, 'effective_port', None)

    def get_url(self) -> str:
        """
        Returns the full url to access this server, usually http://127.0.0.1:<os assigned port>/
        """
        return f'http://{self.__host}:{self.get_effective_port()}{self.__path}'

    @staticmethod
    def bool_to_icon(item: bool) -> str:
        icon = 'x'
        if item:
            icon = 'check'

        return f'<i class="bi bi-{icon}"></i>'

    @staticmethod
    def is_list(item: Any) -> bool:
        return isinstance(item, list)

    @staticmethod
    def is_dict(item: Any) -> bool:
        return isinstance(item, dict)

    @staticmethod
    def timestamp_to_datetime(item: int) -> datetime:
        return datetime.datetime.fromtimestamp(item)

    @staticmethod
    def seconds_to_format(item: int) -> str:
        return str(datetime.timedelta(seconds=item))

    @staticmethod
    def strftime(item: datetime, datetime_format: str) -> str:
        return item.strftime(datetime_format)


class NamerWebServer(GenericWebServer):
    __namer_config: NamerConfig
    __command_queue: Queue

    def __init__(self, namer_config: NamerConfig, command_queue: Queue):
        self.__namer_config = namer_config
        self.__command_queue = command_queue
        webroot = '/' if not self.__namer_config.web_root else self.__namer_config.web_root
        blueprints = [
            web.get_routes(self.__namer_config, self.__command_queue),
            api.get_routes(self.__namer_config, self.__command_queue),
        ]

        super().__init__(self.__namer_config.host, self.__namer_config.port, webroot, blueprints)


class CustomJSONProvider(JSONProvider):
    def dumps(self, obj: Any, **kwargs: Any):
        return orjson.dumps(obj, option=orjson.OPT_PASSTHROUGH_SUBCLASS, default=default).decode('UTF-8')

    def loads(self, s: str | bytes, **kwargs: Any):
        return orjson.loads(s)


def default(obj):
    if isinstance(obj, ImageHash):
        return str(obj)

    if isinstance(obj, (numpy.int_, numpy.intc, numpy.intp, numpy.int8, numpy.int16, numpy.int32, numpy.int64, numpy.uint8, numpy.uint16, numpy.uint32, numpy.uint64)):
        return int(obj)

    elif isinstance(obj, (numpy.float_, numpy.float16, numpy.float32, numpy.float64)):
        return float(obj)

    elif isinstance(obj, (numpy.complex_, numpy.complex64, numpy.complex128)):
        return {
            'real': obj.real,
            'imag': obj.imag
        }

    elif isinstance(obj, (numpy.ndarray,)):
        return obj.tolist()

    elif isinstance(obj, (numpy.bool_)):
        return bool(obj)

    elif isinstance(obj, (numpy.void)):
        return None

    return _default(obj)
