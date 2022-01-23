import time
import os
import configparser
import sys
import traceback
from namer import process, NamerConfig
from pathlib import PurePath

from watchdog.observers.polling import PollingObserver
from watchdog.events import PatternMatchingEventHandler, FileSystemEvent, FileSystemMovedEvent


def doneCopying(file: str) -> bool:
    size_past = 0
    while True:
        time.sleep(2)
        if not os.path.exists(file):
            return False  
        size_now = os.path.getsize(file)
        if size_now == size_past:            
            return True
        else:
            size_past = size_now


class MovieEventHandler(PatternMatchingEventHandler):
    namerConfig: NamerConfig
   
    def __init__(self, namerConfig: NamerConfig):
        super().__init__(patterns=["**/*.mp4"],case_sensitive=False,ignore_directories=True,ignore_patterns=None )
        self.namerConfig = namerConfig

    def on_moved(self, event: FileSystemMovedEvent):
        self.process(event.dest_path)

    def on_closed(self, event: FileSystemEvent):
        self.process(event.src_path)    

    def on_created(self, event: FileSystemEvent):
        self.process(event.src_path)    

    def process(self, path: str):
        print("called")
        detected = PurePath(os.path.relpath(path,self.namerConfig.watchdir)).parts[0]
        dir = os.path.join(self.namerConfig.watchdir, detected)
        print("detected: {}".format(detected))
        print("dir: {}".format(dir))
        try:
            if doneCopying(path) and (os.path.getsize(path) / (1024*1024) > self.namerConfig.min_file_size): #more than 300 megs.
                process(path, self.namerConfig)
        except Exception as ex:
            try:
                exc_info = sys.exc_info()
                try:
                    print("Error handling {}: \n {}".format(dir, ex))
                except:
                    pass
            finally:
                # Display the *original* exception
                traceback.print_exception(*exc_info)
                del exc_info            

class MovieWatcher:
    def __init__(self, namerConfig: NamerConfig):
        self.__src_path = namerConfig.watchdir
        self.__event_handler = MovieEventHandler(namerConfig)
        self.__event_observer = PollingObserver()

    def run(self):
        self.start()
        try:
            while True:
                time.sleep(3)
        except KeyboardInterrupt:
            self.stop()

    def start(self):
        self.__schedule()
        self.__event_observer.start()

    def stop(self):
        self.__event_observer.stop()
        self.__event_observer.join()

    def __schedule(self):
        self.__event_observer.schedule(
            self.__event_handler,
            self.__src_path,
            recursive=True
        )

if __name__ == "__main__":
    print("Porndb scene watcher....")
    if os.environ.get('BUILD_DATE'):
        build_date = os.environ.get('BUILD_DATE')
        print("Built on: {}".format(build_date))
    if os.environ.get('GIT_HASH'):
        git_hash = os.environ.get('GIT_HASH')
        print("Git Hash: {}".format(git_hash))
        
    namer_cfg = './namer.cfg'
    if os.environ.get('NAMER_CONFIG'):
        namer_cfg = os.environ.get('NAMER_CONFIG')
    config = configparser.ConfigParser()
    config.read(namer_cfg)
    namerConfig = NamerConfig()
    namerConfig.language = config['namer']['language']
    namerConfig.watchdir = config['namer']['watch_dir']
    namerConfig.workingdir = config['namer']['work_dir']
    namerConfig.successfuldir = config['namer']['dest_dir']
    namerConfig.porndb_token = config['namer']['porndb_token']
    namerConfig.min_file_size = int(config['namer']['min_file_size'])
    namerConfig.use_dir_name = config['namer']['use_dir_name'].upper() == "TRUE"
    namerConfig.del_other_files = config['namer']['del_other_files'].upper() == "TRUE"
    namerConfig.set_gid = int(config['namer']['set_gid'])
    namerConfig.set_dir_permissions = config['namer']['set_dir_permissions']
    namerConfig.set_file_permissions = config['namer']['set_file_permissions']
    print(namerConfig)
    mw = MovieWatcher(namerConfig)
    mw.run()
    print("exiting")

