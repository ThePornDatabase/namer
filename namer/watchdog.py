"""
A file watching service to rename movie files and move them
to revelant locations after match the file against the porndb.
"""

import re
import shutil
import tempfile
import time
import os
import sys
from pathlib import Path, PurePath
from typing import List
from loguru import logger
from watchdog.observers.polling import PollingObserver
from watchdog.events import PatternMatchingEventHandler, FileSystemEvent, EVENT_TYPE_DELETED, EVENT_TYPE_MOVED
import schedule
from namer.namer import add_extra_artifacts, move_to_final_location, process_file
from namer.types import NamerConfig, default_config, write_log_file

def done_copying(file: Path) -> bool:
    """
    Determines if a file is being copied by checking it's size in 2 second
    increments and seeing if the size has stayed the same.
    """
    size_past = 0
    while True:
        if file is None or not file.exists():
            return False
        size_now = file.stat().st_size
        if size_now == size_past:
            return True
        size_past = size_now
        time.sleep(.2)

@logger.catch
def handle(target_file: Path, namer_config: NamerConfig):
    """
    Responsible for processing and moving new movie files.
    """
    if not target_file.exists() and target_file.is_file():
        return
    relative_path = target_file.relative_to(namer_config.watch_dir)

    # is in a dir:
    detected = PurePath(relative_path).parts[0]
    dir_path = namer_config.watch_dir / detected

    to_process = None
    workingdir = None
    workingfile = None
    if dir_path.is_dir():
        workingdir = Path(namer_config.work_dir) / detected
        logger.info("Moving {} to {} for processing", dir_path, workingdir)
        shutil.move(dir_path,workingdir)
        to_process = workingdir
    else:
        workingfile = Path(namer_config.work_dir) / relative_path
        target_file.rename(workingfile)
        logger.info("Moving {} to {} for processing", target_file, workingfile)
        to_process = workingfile
    result = process_file(to_process, namer_config)

    if result.new_metadata is None:
        if workingdir is not None:
            workingdir.rename(namer_config.failed_dir/ detected)
            logger.info("Moving failed processing {} to {} to retry later", workingdir, namer_config.failed_dir/ detected)
        else:
            newvideo = namer_config.failed_dir / relative_path
            workingfile.rename(newvideo)
            logger.info("Moving failed processing {} to {} to retry later", workingfile, newvideo)
            write_log_file(newvideo, result.search_results, namer_config)
    else:
        # Move the directory if desired.
        if (
            len(PurePath(result.final_name_relative).parts) > 1
            and workingdir is not None
            and namer_config.del_other_files is False
        ):
            target = namer_config.dest_dir / PurePath(result.final_name_relative).parts[0]
            if not target.exists():
                shutil.move(workingdir, target)
                logger.info("Moving success processed dir {} to {}", workingdir, target)
                result.video_file = namer_config.dest_dir / result.final_name_relative
        # Rename the file to dest name.
        newfile = move_to_final_location(
            result.video_file,
            namer_config.dest_dir,
            namer_config.new_relative_path_name,
            result.new_metadata)
        result.video_file = newfile
        logger.info("Moving success processed file {} to {}", result.video_file, newfile)

        # Delete the workingdir if it still exists.
        if workingdir is not None and workingdir.exists():
            shutil.rmtree(workingdir, ignore_errors=True)

        # Generate/aggregate extra artifacts if desired.
        add_extra_artifacts(result, namer_config)



def retry_failed(namer_config: NamerConfig):
    """
    Moves the contents from the failed dir to the watch dir to attempt reprocessing.
    """
    logger.info("Retry failed items:")
    for file in list(namer_config.failed_dir.iterdir()):
        shutil.move( namer_config.failed_dir / file.name, namer_config.watch_dir / file.name )

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

    def on_any_event(self, event: FileSystemEvent):
        file_path = None
        if event.event_type == EVENT_TYPE_MOVED:
            file_path = event.dest_path
        elif event.event_type != EVENT_TYPE_DELETED:
            file_path = event.src_path
        if file_path is not None:
            path = Path(file_path)
            relative_path = str(path.relative_to(self.namer_config.watch_dir))
            logger.info("watchdog process called for {}", relative_path)
            if (re.search(self.namer_config.ignored_dir_regex, relative_path) is None
                and path.exists()
                and done_copying(path)
                and (path.stat().st_size / (1024*1024) > self.namer_config.min_file_size)):
                # Extra wait time in case other files are copies in as well.
                if self.namer_config.del_other_files is True:
                    time.sleep(self.namer_config.extra_sleep_time)
                handle(path, self.namer_config)

class MovieWatcher:
    """
    Watches a configured dir for new files and attempts
    to process them and move to a destination dir.

    If a failure occures moves the new files to a failed dir.

    See NamerConfig
    """
    def __init__(self, namer_config: NamerConfig):
        self.__namer_config = namer_config
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
        config = self.__namer_config
        logger.info("Start porndb scene watcher.... watching: {}",config.watch_dir)
        if os.environ.get('PROJECT_VERSION'):
            project_version = os.environ.get('PROJECT_VERSION')
            print(f"Namer version: {project_version}")
        if os.environ.get('BUILD_DATE'):
            build_date = os.environ.get('BUILD_DATE')
            print(f"Built on: {build_date}")
        if os.environ.get('GIT_HASH'):
            git_hash = os.environ.get('GIT_HASH')
            print(f"Git Hash: {git_hash}")
        self.__schedule()
        self.__event_observer.start()
        # touch all existing movie files.
        files: List[Path] = []
        for file in self.__namer_config.watch_dir.rglob('*.*'):
            if file.is_file() and file.suffix in ('.mkv', '.mp4'):
                files.append(file)
        for file in files:
            if file.exists() and file.is_file():
                handle(file, self.__namer_config)

    def stop(self):
        """
        stops a background thread to check for files.
        Waits for the event processor to complete.
        """
        logger.info("exiting")
        self.__event_observer.stop()
        self.__event_observer.join()
        logger.info("exited")

    def __schedule(self):
        self.__event_observer.schedule(
            self.__event_handler,
            self.__src_path,
            recursive=True
        )


def create_watcher(namer_watchdog_config: NamerConfig) -> MovieWatcher:
    """
    Configure and start a watchdog looking for new Movies.
    """
    logger.remove()
    logger.add(sys.stdout, format="{time} {level} {message}", level="INFO")
    logger.info(str(namer_watchdog_config))
    if not namer_watchdog_config.verify_watchdog_config():
        sys.exit(-1)
    if namer_watchdog_config.retry_time is not None:
        schedule.every().day.at(namer_watchdog_config.retry_time).do(lambda: retry_failed(namer_watchdog_config))
    movie_watcher = MovieWatcher(namer_watchdog_config)
    return movie_watcher


if __name__ == "__main__":
    create_watcher(default_config()).run()
