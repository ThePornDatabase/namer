import argparse
import sys
from pathlib import Path

from flask import Flask, render_template

from namer.types import default_config

app = Flask(__name__, static_url_path='/', static_folder='public', template_folder='templates')
config = default_config()


@app.route('/')
def index():
    files = {
        'danger': get_files(config.failed_dir),
        'warning': get_files(config.work_dir),
        'light': get_files(config.watch_dir),
        'success': get_files(config.dest_dir),
    }

    return render_template('files.html', files=files)


def get_files(path: Path) -> list[Path]:
    return [file for file in path.rglob('*.*') if file.is_file() and file.suffix[1:] in config.target_extensions]


def main(arg_list: list[str]):
    parser = argparse.ArgumentParser(description='Namer webserver')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args(arg_list)
    app.run(debug=args.debug)


if __name__ == '__main__':
    main(sys.argv[1:])
