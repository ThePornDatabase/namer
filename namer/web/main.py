import argparse
import sys

from flask import Flask, render_template, url_for
from loguru import logger

from namer.web.helpers import has_no_empty_params, get_files, config

app = Flask(__name__, static_url_path='/', static_folder='public', template_folder='templates')


@app.route('/')
def index():
    data = []
    for rule in app.url_map.iter_rules():
        if 'GET' in rule.methods and has_no_empty_params(rule):
            url = url_for(rule.endpoint, **(rule.defaults or {}))
            data.append((url, rule.endpoint))

    return render_template('index.html', links=data)


@app.route('/files')
def files():
    data = {
        'danger': get_files(config.failed_dir),
        'warning': get_files(config.work_dir),
        'light': get_files(config.watch_dir),
        'success': get_files(config.dest_dir),
    }

    return render_template('files.html', files=data)


@logger.catch
def main(arg_list: list[str]):
    parser = argparse.ArgumentParser(description='Namer webserver')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Server host')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Server port')
    args = parser.parse_args(arg_list)

    if args.debug:
        app.run(debug=args.debug, host=args.host, port=args.port)
    else:
        from waitress import serve
        serve(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main(sys.argv[1:])
