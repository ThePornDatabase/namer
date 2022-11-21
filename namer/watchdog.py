"""
A file watching service to rename movie files and move them
to relevant locations after match the file against the porndb.
"""

import os
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

from namer.configuration import NamerConfig
from namer.configuration_utils import default_config, verify_configuration
from namer.command import gather_target_files_from_dir, is_interesting_movie, make_command_relative_to, move_command_files, Command
from namer.name_formatter import PartialFormatter
from namer.namer import process_file
from namer.web.server import NamerWebServer


def done_copying(file: Optional[Path]) -> bool:
    """
    Determines if a file is being copied by checking its size in 2 second
    increments and seeing if the size has stayed the same.
    """
    if not file or not file.exists():
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
    for log_file in namer_config.failed_dir.rglob("**/*_namer.json.gz"):
        log_file.unlink()

    # move all files back to watch dir.
    for file in gather_target_files_from_dir(namer_config.failed_dir, namer_config):
        target = file.target_directory.name if file.parsed_dir_name and file.target_directory else file.target_movie_file.name
        shutil.move(namer_config.failed_dir / target, namer_config.watch_dir / target)


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

    __namer_config: NamerConfig

    def __init__(self, namer_config: NamerConfig, queue: Queue):
        super().__init__(patterns=["*.*"], case_sensitive=is_fs_case_sensitive(), ignore_directories=True, ignore_patterns=None)
        self.__namer_config = namer_config
        self.__command_queue = queue

    def on_any_event(self, event: FileSystemEvent):
        file_path = None
        if event.event_type == EVENT_TYPE_MOVED:
            file_path = event.dest_path  # type: ignore
        elif event.event_type != EVENT_TYPE_DELETED:
            file_path = event.src_path

        if file_path:
            path = Path(file_path)
            relative_path = str(path.relative_to(self.__namer_config.watch_dir))
            if not self.__namer_config.ignored_dir_regex.search(relative_path) and done_copying(path) and is_interesting_movie(path, self.__namer_config):
                logger.info("watchdog process called for {}", relative_path)

                # Extra wait time in case other files are copies in as well.
                if self.__namer_config.del_other_files:
                    time.sleep(self.__namer_config.extra_sleep_time)

                self.prepare_file_for_processing(path)

    @logger.catch
    def prepare_file_for_processing(self, path: Path):
        command = make_command_relative_to(input_dir=path, relative_to=self.__namer_config.watch_dir, config=self.__namer_config)
        working_command = move_command_files(command, self.__namer_config.work_dir)
        if working_command is not None:
            self.__command_queue.put(working_command)


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
        self.__started = False
        self.__stopped = False
        self.__namer_config = namer_config
        self.__src_path = namer_config.watch_dir
        self.__event_observer = PollingObserver()
        self.__webserver: Optional[NamerWebServer] = None
        self.__command_queue: Queue = Queue()
        self.__worker_thread: Thread = Thread(target=self.__processing_thread, daemon=True)
        self.__event_handler = MovieEventHandler(namer_config, self.__command_queue)
        self.__background_thread: Optional[Thread] = None

    def getConfig(self) -> NamerConfig:
        return self.__namer_config

    def run(self):
        """
        Checks for new files in 3 second intervals,
        needed if running in docker as events aren't properly passed in.
        """
        if not self.__started:
            self.start()
            if self.__namer_config.web:
                self.__webserver = NamerWebServer(self.__namer_config, self.__command_queue)
                self.__webserver.start()

            try:
                while not self.__stopped:
                    schedule.run_pending()
                    time.sleep(3)
                self.stop()
            except KeyboardInterrupt:
                self.stop()

            self.__started = False
            self.__stopped = False

    def __enter__(self):
        self.__background_thread = Thread(target=self.run)
        self.__background_thread.start()

        tries = 0
        while not self.get_web_port() and tries < 20:
            time.sleep(0.2)
            tries += 1

        if not self.get_web_port:
            raise RuntimeError("application did not get assigned a port within 4 seconds.")

        return self

    def __simple_exit__(self):
        self.stop()
        if self.__background_thread:
            self.__background_thread.join()
            self.__background_thread = None

    def __exit__(self, exc_type, exc_value, traceback):
        self.__simple_exit__()

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
            relative_path = str(file.relative_to(self.__namer_config.watch_dir))
            if not config.ignored_dir_regex.search(relative_path) and done_copying(file) and is_interesting_movie(file, self.__namer_config):
                self.__event_handler.prepare_file_for_processing(file)

    def stop(self):
        """
        stops a background thread to check for files.
        Waits for the event processor to complete.
        """
        if not self.__stopped:
            self.__stopped = True
            logger.info("Exiting")
            self.__event_observer.stop()
            self.__event_observer.join()
            if self.__webserver:
                self.__webserver.stop()
            self.__command_queue.put(None)
            self.__command_queue.join()
            logger.info("Exited")

    def get_web_port(self) -> Optional[int]:
        if self.__webserver is not None:
            return self.__webserver.get_effective_port()

    def __schedule(self):
        self.__event_observer.schedule(self.__event_handler, str(self.__src_path), recursive=True)


def create_watcher(namer_watchdog_config: NamerConfig) -> MovieWatcher:
    """
    Configure and start a watchdog looking for new Movies.
    """
    logger.remove()
    level = 'DEBUG' if namer_watchdog_config.debug else 'INFO'
    logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level.icon} {level: <8}</level> | {message}", level=level, diagnose=namer_watchdog_config.diagnose_errors)
    logger.info(namer_watchdog_config)

    if not verify_configuration(namer_watchdog_config, PartialFormatter()):
        sys.exit(-1)

    if namer_watchdog_config.retry_time:
        schedule.every().day.at(namer_watchdog_config.retry_time).do(lambda: retry_failed(namer_watchdog_config))

    movie_watcher = MovieWatcher(namer_watchdog_config)

    return movie_watcher


if __name__ == "__main__":
    create_watcher(default_config()).run()
