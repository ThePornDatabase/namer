"""
A file watching service to rename movie files and move them
to relevant locations after match the file against the porndb.
"""

import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import List, Optional

import schedule
from loguru import logger
from watchdog.events import EVENT_TYPE_DELETED, EVENT_TYPE_MOVED, FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers.polling import PollingObserver

from namer.fileutils import make_command_relative_to, is_interesting_movie, move_command_files
from namer.namer import process_file
from namer.types import Command, default_config, NamerConfig
from namer.web.server import WebServer


def done_copying(file: Optional[Path]) -> bool:
    """
    Determines if a file is being copied by checking its size in 2 second
    increments and seeing if the size has stayed the same.
    """
    if file is None or file.exists() is False:
        return False
    while True:
        try:
            # pylint: disable=consider-using-with
            buffered_reader = open(file, mode="rb")
            buffered_reader.close()
            break
        except PermissionError:
            time.sleep(0.2)
    return True


@logger.catch
def handle(command: Command):
    """
    Responsible for processing and moving new movie files.
    """
    process_file(command)


def retry_failed(namer_config: NamerConfig):
    """
    Moves the contents from the failed dir to the watch dir to attempt reprocessing.
    """
    logger.info("Retry failed items:")
    # remove all old namer log files
    for log_file in namer_config.failed_dir.rglob("**/*_namer.log"):
        log_file.unlink()
    # move all files back to watch dir.
    for file in list(namer_config.failed_dir.iterdir()):
        shutil.move(namer_config.failed_dir / file.name, namer_config.watch_dir / file.name)


def is_fs_case_sensitive():
    """
    Create a temporary file to determine if a filesystem is case-sensitive, or not.
    """
    with tempfile.NamedTemporaryFile(prefix="TmP") as tmp_file:
        return not Path(tmp_file.name.lower()).is_file()


class MovieEventHandler(PatternMatchingEventHandler):
    """
    When a new movie file is detected, this class handles the event,
    and passes off the processing to the handler() function above.
    """

    namer_config: NamerConfig

    def __init__(self, namer_config: NamerConfig, queue: Queue):
        super().__init__(patterns=["*.*"], case_sensitive=is_fs_case_sensitive(), ignore_directories=True, ignore_patterns=None)
        self.namer_config = namer_config
        self.command_queue = queue

    def on_any_event(self, event: FileSystemEvent):
        file_path = None
        if event.event_type == EVENT_TYPE_MOVED:
            file_path = event.dest_path  # type: ignore
        elif event.event_type != EVENT_TYPE_DELETED:
            file_path = event.src_path
        if file_path is not None:
            path = Path(file_path)
            relative_path = str(path.relative_to(self.namer_config.watch_dir))
            if re.search(self.namer_config.ignored_dir_regex, relative_path) is None and done_copying(path) and is_interesting_movie(path, self.namer_config):
                logger.info("watchdog process called for {}", relative_path)
                # Extra wait time in case other files are copies in as well.
                if self.namer_config.del_other_files is True:
                    time.sleep(self.namer_config.extra_sleep_time)
                command = make_command_relative_to(input_dir=path, relative_to=self.namer_config.watch_dir, config=self.namer_config)
                working_command = move_command_files(command, self.namer_config.work_dir)
                if working_command is not None:
                    self.command_queue.put(working_command)


class MovieWatcher:
    """
    Watches a configured dir for new files and attempts
    to process them and move to a destination dir.

    If a failure occurs moves the new files to a failed dir.

    See NamerConfig
    """

    def __processing_thread(self):
        while True:
            command = self.__command_queue.get()
            if command is None:
                break
            handle(command)
            self.__command_queue.task_done()
        self.__command_queue.task_done()

    def __init__(self, namer_config: NamerConfig):
        self.__namer_config = namer_config
        self.__src_path = namer_config.watch_dir
        self.__event_observer = PollingObserver()
        self.__webserver: Optional[WebServer] = None
        self.__command_queue: Queue = Queue()
        self.__worker_thread: Thread = Thread(target=self.__processing_thread, daemon=True)
        self.__event_handler = MovieEventHandler(namer_config, self.__command_queue)

    def run(self):
        """
        Checks for new files in 3 second intervals,
        needed if running in docker as events aren't properly passed in.
        """
        self.start()
        if self.__namer_config.web is True:
            self.__webserver = WebServer(self.__namer_config, command_queue=self.__command_queue)
            if self.__webserver:
                Thread(target=self.__webserver.run).start()
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
        logger.info("Start porndb scene watcher.... watching: {}", config.watch_dir)
        if os.environ.get("PROJECT_VERSION"):
            project_version = os.environ.get("PROJECT_VERSION")
            print(f"Namer version: {project_version}")
        if os.environ.get("BUILD_DATE"):
            build_date = os.environ.get("BUILD_DATE")
            print(f"Built on: {build_date}")
        if os.environ.get("GIT_HASH"):
            git_hash = os.environ.get("GIT_HASH")
            print(f"Git Hash: {git_hash}")
        self.__schedule()
        self.__event_observer.start()
        self.__worker_thread.start()
        # touch all existing movie files.
        files: List[Path] = []
        for file in self.__namer_config.watch_dir.rglob("**/*.*"):
            if file.is_file() and file.suffix.lower()[1:] in self.__namer_config.target_extensions:
                files.append(file)
        for file in files:
            if file.exists() and file.is_file():
                command = make_command_relative_to(file, self.__namer_config.watch_dir, self.__namer_config)
                working_command = move_command_files(command, self.__namer_config.work_dir)
                if working_command is not None:
                    self.__command_queue.put(working_command)

    def stop(self):
        """
        stops a background thread to check for files.
        Waits for the event processor to complete.
        """
        logger.info("exiting")
        self.__event_observer.stop()
        self.__event_observer.join()
        if self.__webserver is not None:
            self.__webserver.stop()
        self.__command_queue.put(None)
        self.__command_queue.join()
        logger.info("exited")

    def __schedule(self):
        self.__event_observer.schedule(self.__event_handler, str(self.__src_path), recursive=True)


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
