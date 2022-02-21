"""
A file watching service to rename movie files and move them
to revelant locations after match the file against the porndb.
"""

import shutil
import tempfile
import time
import os
import sys
import traceback
from pathlib import Path, PurePath
import logging
from watchdog.observers.polling import PollingObserver
from watchdog.events import PatternMatchingEventHandler, FileSystemEvent, FileSystemMovedEvent
import schedule
from namer import move_to_final_location, process
from namer_types import NamerConfig, default_config

logger = logging.getLogger('watchdog')


def done_copying(file: Path) -> bool:
    """
    Determines if a file is being copied by checking it's size in 2 second
    increments and seeing if the size has stayed the same.
    """
    size_past = 0
    while True:
        if not file.exists():
            return False
        size_now = file.stat().st_size
        if size_now == size_past:
            return True
        size_past = size_now
        time.sleep(.2)


def handle(target_file: Path, namer_config: NamerConfig):
    """
    Responsible for processing and moving new movie files.
    """
    relative_path = target_file.relative_to(namer_config.watch_dir)

    # is in a dir:
    detected = PurePath(relative_path).parts[0]
    dir_path = namer_config.watch_dir / detected

    to_process = None
    workingdir = None
    workingfile = None
    if dir_path.is_dir():
        workingdir = Path(namer_config.work_dir) / detected
        logger.info("Moving %s to %s for processing", dir_path, workingdir)
        shutil.move(dir_path,workingdir)
        to_process = workingdir
    else:
        workingfile = Path(namer_config.work_dir) / relative_path
        target_file.rename(workingfile)
        logger.info("Moving %s to %s for processing", target_file, workingfile)
        to_process = workingfile
    result = process(to_process, namer_config)

    if result.new_metadata is None:
        if workingdir is not None:
            workingdir.rename(namer_config.failed_dir/ detected)
            logger.info("Moving failed processing %s to %s to retry later", workingdir, namer_config.failed_dir/ detected)
        else:
            newvideo = namer_config.failed_dir / relative_path
            workingfile.rename(newvideo)
            logger.info("Moving failed processing %s to %s to retry later", workingdir, newvideo)
            if result.namer_log_file is not None:
                result.namer_log_file.rename( result.video_file.parent /
                    (result.namer_log_file.stem+"_namer.log"))
    else:
        # See if we should, and can, move the whole dir.
        moved = False
        if (
            len(PurePath(result.final_name_relative).parts) > 1
            and workingdir is not None
            and namer_config.del_other_files is False
        ):
            target = namer_config.dest_dir / PurePath(result.final_name_relative).parts[0]
            if not target.exists():
                shutil.move(workingdir, target)
                moved = True
                logger.info("Moving success processed dir %s to %s", workingdir, target)
        # else just moved the tagged video file and logs.
        if not moved:
            newfile = move_to_final_location(
                result.video_file,
                namer_config.dest_dir,
                namer_config.new_relative_path_name,
                result.new_metadata)
            if result.namer_log_file is not None:
                shutil.move(result.namer_log_file, newfile.parent / (newfile.stem+"_namer.log"))
            logger.info("Moving success processed file %s to %s", workingfile, newfile)
            if workingdir is not None:
                shutil.rmtree(workingdir, ignore_errors=True)

def retry_failed(namer_config: NamerConfig):
    """
    Moves the contents from the failed dir to the watch dir to attempt reprocessing.
    """
    logger.info("Retry failed items:")
    for file in list(namer_config.failed_dir.iterdir()):
        shutil.move( namer_config.failed_dir / file, namer_config.watch_dir / file )

def is_fs_case_sensitive():
    """
    Create a temporary file to determine if a filesystem is case sensitive, or not.
    """
    with tempfile.NamedTemporaryFile(prefix='TmP') as tmp_file:
        return(not os.path.exists(tmp_file.name.lower()))

class MovieEventHandler(PatternMatchingEventHandler):
    """
    When a new movie file is detected, this class handles the event,
    and passes off the processing to the handler() function above.
    """
    namer_config: NamerConfig

    def __init__(self, namer_config: NamerConfig):
        super().__init__(patterns=["**/*.mp4", "**/*.mkv", "**/*.MP4", "**/*.MKV"],
                         case_sensitive=is_fs_case_sensitive(), ignore_directories=True, ignore_patterns=None)
        self.namer_config = namer_config

    def on_moved(self, event: FileSystemMovedEvent):
        self.process(event.dest_path)

    def on_closed(self, event: FileSystemEvent):
        self.process(event.src_path)

    def on_created(self, event: FileSystemEvent):
        self.process(event.src_path)

    def process(self, path_in: str):
        """
        Watch for and process new files, after ensuring the file is fully moved in to place.
        """
        path = Path(path_in)
        logger.info("watchdog process called")
        if done_copying(path) and (path.stat().st_size / (1024*1024) > self.namer_config.min_file_size):
            try:
                handle(path, self.namer_config)
            except Exception as ex:  # pylint: disable=broad-except
                try:
                    exc_info = sys.exc_info()
                    try:
                        logger.error("Error handling %s: \n %s", path, ex)
                    except Exception: # pylint: disable=broad-except
                        pass
                finally:
                    # Display the *original* exception
                    traceback.print_exception(*exc_info)
                    del exc_info


class MovieWatcher:
    """
    Watches a configured dir for new files and attempts
    to process them and move to a destination dir.

    If a failure occures moves the new files to a failed dir.

    See NamerConfig
    """
    def __init__(self, namer_config: NamerConfig):
        self.__src_path = namer_config.watch_dir
        self.__event_handler = MovieEventHandler(namer_config)
        self.__event_observer = PollingObserver()

    def run(self):
        """
        Checks for new files in 3 second intervals,
        needed if running in docker as events aren't properly passed in.
        """
        self.start()
        try:
            while True:
                schedule.run_pending()
                time.sleep(3)
        except KeyboardInterrupt:
            self.stop()

    def start(self):
        """
        starts a background thread to check for files.
        """
        self.__schedule()
        self.__event_observer.start()

    def stop(self):
        """
        stops a background thread to check for files.
        Waints for the event processor to complete.
        """
        self.__event_observer.stop()
        self.__event_observer.join()

    def __schedule(self):
        self.__event_observer.schedule(
            self.__event_handler,
            self.__src_path,
            recursive=True
        )


def watch_for_movies(config: NamerConfig):
    """
    Configure and start a watchdog looking for new Movies.
    """
    logger.info(str(config))
    logger.info("Start porndb scene watcher.... watching: %s",config.watch_dir)
    if os.environ.get('BUILD_DATE'):
        build_date = os.environ.get('BUILD_DATE')
        print(f"Built on: {build_date}")
    if os.environ.get('GIT_HASH'):
        git_hash = os.environ.get('GIT_HASH')
        print(f"Git Hash: {git_hash}")
    movie_watcher = MovieWatcher(config)
    movie_watcher.run()
    logger.info("exiting")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    namer_watchdog_config=default_config()
    namer_watchdog_config.verify_watchdog_config()
    if namer_watchdog_config.retry_time is not None:
        schedule.every().day.at(namer_watchdog_config.retry_time).do(lambda: retry_failed(namer_watchdog_config))
    watch_for_movies(namer_watchdog_config)
