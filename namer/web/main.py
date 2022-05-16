"""
Creates a webserver allowing the renaming of failed files.
"""

import argparse
import sys
from typing import List

from loguru import logger

from namer.types import default_config
from namer.web.server import WebServer


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

    web = WebServer(local_config, args.debug)
    web.run()


if __name__ == '__main__':
    main(sys.argv[1:])
