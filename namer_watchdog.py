import pathlib
import shutil
import time
import os
import sys
import traceback
from namer import process
from namer_types import NamerConfig, defaultConfig
from pathlib import PurePath
import logging
from watchdog.observers.polling import PollingObserver
from watchdog.events import PatternMatchingEventHandler, FileSystemEvent, FileSystemMovedEvent

logger = logging.getLogger('watchdog')

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

def handle(target_file: str, namerConfig: NamerConfig):
    relative_path = os.path.relpath(target_file,namerConfig.watch_dir)
    
    #is in a dir:
    detected = PurePath(relative_path).parts[0]
    dir_path = os.path.join(namerConfig.watch_dir, detected)
    
    to_process=None
    workingdir=None
    workingfile=None
    if os.path.isdir(dir_path):
        workingdir = os.path.join(namerConfig.work_dir,detected)
        os.rename(dir_path, workingdir)
        to_process=workingdir
    else:
        workingfile = os.path.join(namerConfig.work_dir,relative_path)
        os.rename(target_file,workingfile)
        to_process=workingfile
    result = process(to_process, namerConfig)
    
    if not result.found:
        if workingdir is not None:
            os.rename(workingdir, os.path.join(namerConfig.failed_dir,detected))
        else:
            newvideo = os.path.join(namerConfig.failed_dir,relative_path)
            os.rename(workingfile, newvideo)
            os.rename(result.namer_log_file, os.path.splitext(newvideo)[0]+"_namer.log")
    else:        
        newfile = os.path.join(namerConfig.dest_dir, result.final_name_relative)
        if len(PurePath(result.final_name_relative).parts) > 1 and workingdir is not None and namerConfig.del_other_files == False: 
            shutil.move(workingdir, os.path.dirname(newfile))
        else:
            os.makedirs(os.path.dirname(newfile), exist_ok=True)
            shutil.move(result.video_file, newfile)
            shutil.move(result.namer_log_file, os.path.splitext(newfile)[0]+"_namer.log")
            shutil.rmtree(workingdir, ignore_errors=True)


class MovieEventHandler(PatternMatchingEventHandler):
    namerConfig: NamerConfig
   
    def __init__(self, namerConfig: NamerConfig):
        super().__init__(patterns=["**/*.mp4","**/*.mkv","**/*.MP4","**/*.MKV"],case_sensitive=True,ignore_directories=True,ignore_patterns=None )
        self.namerConfig = namerConfig

    def on_moved(self, event: FileSystemMovedEvent):
        self.process(event.dest_path)

    def on_closed(self, event: FileSystemEvent):
        self.process(event.src_path)    

    def on_created(self, event: FileSystemEvent):
        self.process(event.src_path)    

    def process(self, path: str):
        logger.info("watchdog process called")
        if doneCopying(path): # and (os.path.getsize(path)/ (1024*1024) > self.namerConfig.min_file_size):           
            try:
                handle(path, self.namerConfig)
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
        self.__src_path = namerConfig.watch_dir
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

def watchForMovies(config: NamerConfig):
    logger.info(str(config))
    logger.info("Start porndb scene watcher.... watching: {}".format(config.watch_dir))
    if os.environ.get('BUILD_DATE'):
        build_date = os.environ.get('BUILD_DATE')
        print("Built on: {}".format(build_date))
    if os.environ.get('GIT_HASH'):
        git_hash = os.environ.get('GIT_HASH')
        print("Git Hash: {}".format(git_hash))
    mw = MovieWatcher(config)
    mw.run()
    logger.info("exiting")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    watchForMovies(defaultConfig())
