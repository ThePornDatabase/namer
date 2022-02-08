"""
A file watching service to rename movie files and move them
to revelant locations after match the file against the porndb.
"""

import shutil
import time
import os
import sys
import traceback
from pathlib import PurePath
import logging
from watchdog.observers.polling import PollingObserver
from watchdog.events import PatternMatchingEventHandler, FileSystemEvent, FileSystemMovedEvent
import schedule
from namer import process
from namer_types import NamerConfig, default_config

logger = logging.getLogger('watchdog')


def done_copying(file: str) -> bool:
    """
    Determines if a file is being copied by checking it's size in 2 second
    increments and seeing if the size has stayed the same.
    """
    size_past = 0
    while True:
        time.sleep(2)
        if not os.path.exists(file):
            return False
        size_now = os.path.getsize(file)
        if size_now == size_past:
            return True
        size_past = size_now


def handle(target_file: str, namer_config: NamerConfig):
    """
    Responsible for processing and moving new movie files.
    """
    relative_path = os.path.relpath(target_file, namer_config.watch_dir)

    # is in a dir:
    detected = PurePath(relative_path).parts[0]
    dir_path = os.path.join(namer_config.watch_dir, detected)

    to_process = None
    workingdir = None
    workingfile = None
    if os.path.isdir(dir_path):
        workingdir = os.path.join(namer_config.work_dir, detected)
        os.rename(dir_path, workingdir)
        to_process = workingdir
    else:
        workingfile = os.path.join(namer_config.work_dir, relative_path)
        os.rename(target_file, workingfile)
        to_process = workingfile
    result = process(to_process, namer_config)

    if not result.found:
        if workingdir is not None:
            os.rename(workingdir, os.path.join(
                namer_config.failed_dir, detected))
        else:
            newvideo = os.path.join(namer_config.failed_dir, relative_path)
            os.rename(workingfile, newvideo)
            os.rename(result.namer_log_file, os.path.splitext(
                newvideo)[0]+"_namer.log")
    else:
        newfile = os.path.join(namer_config.dest_dir,
                               result.final_name_relative)
        if (
            len(PurePath(result.final_name_relative).parts) > 1
            and workingdir is not None
            and namer_config.del_other_files is False
        ):
            shutil.move(workingdir, os.path.dirname(newfile))
        else:
            os.makedirs(os.path.dirname(newfile), exist_ok=True)
            shutil.move(result.video_file, newfile)
            shutil.move(result.namer_log_file,
                        os.path.splitext(newfile)[0]+"_namer.log")
            shutil.rmtree(workingdir, ignore_errors=True)

def retry_failed(namer_config: NamerConfig):
    """
    Moves the contents from the failed dir to the watch dir to attempt reprocessing.
    """
    logger.info("Retry failed items:")
    for file in os.listdir(namer_config.failed_dir):
        shutil.move(os.path.join(namer_config.failed_dir, file), os.path.join(namer_config.watch_dir,file))

class MovieEventHandler(PatternMatchingEventHandler):
    """
    When a new movie file is detected, this class handles the event,
    and passes off the processing to the handler() function above.
    """
    namer_config: NamerConfig

    def __init__(self, namer_config: NamerConfig):
        super().__init__(patterns=["**/*.mp4", "**/*.mkv", "**/*.MP4", "**/*.MKV"],
                         case_sensitive=True, ignore_directories=True, ignore_patterns=None)
        self.namer_config = namer_config

    def on_moved(self, event: FileSystemMovedEvent):
        self.process(event.dest_path)

    def on_closed(self, event: FileSystemEvent):
        self.process(event.src_path)

    def on_created(self, event: FileSystemEvent):
        self.process(event.src_path)

    def process(self, path: str):
        """
        Watch for and process new files, after ensuring the file is fully moved in to place.
        """
        logger.info("watchdog process called")
        if done_copying(path) and (os.path.getsize(path)/ (1024*1024) > self.namer_config.min_file_size):
            try:
                handle(path, self.namer_config)
            except Exception as ex:  # pylint: disable=broad-except
                try:
                    exc_info = sys.exc_info()
                    try:
                        print(f"Error handling {dir}: \n {ex}")
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
    namer_watchdog_config = default_config()
    namer_watchdog_config.verify_config()
    if namer_watchdog_config.retry_time is not None:
        schedule.every().day.at(namer_watchdog_config.retry_time).do(lambda: retry_failed(namer_watchdog_config))
    watch_for_movies(namer_watchdog_config)
