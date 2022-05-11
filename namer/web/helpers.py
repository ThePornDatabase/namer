from pathlib import Path

from namer.types import default_config

config = default_config()


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


def get_files(path: Path) -> list[Path]:
    return [file for file in path.rglob('*.*') if file.is_file() and file.suffix[1:] in config.target_extensions]
