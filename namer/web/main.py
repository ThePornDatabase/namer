import argparse
import sys

from flask import Flask, jsonify, render_template, request, url_for
from htmlmin.main import minify
from waitress import serve

from namer.web.helpers import config, get_files, get_search_results, has_no_empty_params, make_rename

app = Flask(__name__, static_url_path='/', static_folder='public', template_folder='templates')


@app.route('/')
def index():
    data = []
    for rule in app.url_map.iter_rules():
        if 'GET' in rule.methods and has_no_empty_params(rule):
            url = url_for(rule.endpoint, **(rule.defaults or {}))
            data.append((url, rule.endpoint))

    return render_template('pages/index.html', links=data)


@app.route('/failed')
def files():
    data = get_files(config.failed_dir)
    return render_template('pages/failed.html', files=data)


@app.route('/render', methods=['POST'])
def render():
    data = request.json
    template = data.get('template')
    data = data.get('data')

    template_file = f'components/{template}.html'
    data = render_template(template_file, data=data)

    res = {
        'response': minify(data),
    }

    return jsonify(res)


@app.route('/get_search', methods=['POST'])
def get_results():
    data = request.json
    res = get_search_results(data['query'], data['file'])
    return jsonify(res)


@app.route('/rename', methods=['POST'])
def rename():
    data = request.json
    res = make_rename(data['file'], data['scene_id'])
    return jsonify(res)


@app.after_request
def response_minify(response):
    if 'text/html' in response.content_type:
        response.set_data(minify(response.get_data(as_text=True)))

        return response

    return response


def main(arg_list: list[str]):
    parser = argparse.ArgumentParser(description='Namer webserver')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Server host')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Server port')
    args = parser.parse_args(arg_list)

    if args.debug:
        app.run(debug=args.debug, host=args.host, port=args.port)
    else:
        serve(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main(sys.argv[1:])
