"""
Namer, the porn db file renamer. It can be a command line tool to rename mp4/mkv/avi/mov/flv files and to embed tags in mp4's,
or a watchdog service to do the above watching a directory for new files.  File names are assumed to be of
the form SITE.[YY]YY.MM.DD.String.of.performers.and.or.scene.name.<IGNORED_INFO>.[mp4|mkv|...].   In the name, read the
periods, ".", as any number of spaces " ", dashes "-", or periods ".".

Provided you have an access token to the porndb (free sign up) https://www.metadataapi.net/, this program will
attempt to match your file's name to search results from the porndb.   Please note that the site must at least be
a substring of the actual site name on the porndb, and the date must be within one day or the release date on the
porndb for a match to be considered.  If the log file flag is enabled then a <original file name minus ext>_namer.json.gz
file will be written with all the potential matches sorted, descending by how closely the scene name/performer names
match the file.
"""
import sys
from datetime import timedelta
from pathlib import Path
from typing import List

from loguru import logger
from requests_cache import CachedSession

import namer.metadataapi
import namer.namer
import namer.watchdog
import namer.web
from namer.configuration_utils import default_config
from namer.models import db

DESCRIPTION = (
    namer.namer.DESCRIPTION + """

    The first argument should be 'watchdog', 'rename', 'suggest', or 'help' to see this message, for more help on rename, call
    namer 'namer rename -h'

    watchdog and help take no arguments (please see the config file example https://github.com/4c0d3r/namer/blob/main/namer.cfg)

    'suggest' takes a file name as input and will output a suggested file name.
    """
)


def create_default_config_if_missing():
    """
    Find or create config.
    """
    config_file = Path(".namer.conf")
    print("Creating default config file here: {}", config_file)
    print("please edit the token or any other settings whose defaults you want changed.")


def main(arg_list: List[str]):
    """
    Call main method in namer.namer or namer.watchdog.
    """
    logger.remove()
    config = default_config()

    # create a CachedSession objects for request caching.
    if config.use_requests_cache:
        cache_file = config.database_path / 'namer_cache'
        expire_time = timedelta(minutes=config.requests_cache_expire_minutes)
        config.cache_session = CachedSession(str(cache_file), backend='sqlite', expire_after=expire_time, ignored_parameters=['Authorization'])

    if config.use_database:
        db_file = config.database_path / 'namer_database.sqlite'
        db.bind(provider='sqlite', filename=str(db_file), create_db=True)
        db.generate_mapping(create_tables=True)

    arg1 = None if len(arg_list) == 0 else arg_list[0]
    if arg1 == "watchdog":
        level = 'DEBUG' if config.debug else 'INFO'
        logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level.icon} {level: <8}</level> | {message}", level=level, diagnose=config.diagnose_errors)
        namer.watchdog.create_watcher(config).run()
    elif arg1 == "rename":
        namer.namer.main(arg_list[1:])
    elif arg1 == "suggest":
        namer.metadataapi.main(arg_list[1:])
    elif arg1 in ["-h", "help", None]:
        print(DESCRIPTION)

    if config.use_requests_cache and config.cache_session:
        config.cache_session.cache.delete(expired=True)


if __name__ == "__main__":
    main(sys.argv[1:])
