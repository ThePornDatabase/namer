.. |logo| image:: ./logo/namer.png
  :width: 80
  :class: display: inline flow; align: left

##############
|logo| Namer
##############

.. image:: https://github.com/ThePornDatabase/namer/actions/workflows/ci.yml/badge.svg?
  :target: https://github.com/ThePornDatabase/namer/actions/workflows/ci.yml/
.. image:: https://codecov.io/gh/ThePornDatabase/namer/branch/main/graph/badge.svg?token=4MQEN2NUKZ
  :target: https://codecov.io/gh/ThePornDatabase/namer
.. image:: https://badge.fury.io/py/namer.svg?
  :target: https://badge.fury.io/py/namer
.. image:: https://img.shields.io/pypi/dm/namer?logo=pypi&logoColor=fff
  :target: https://pypi.org/project/namer
.. image:: https://static.pepy.tech/personalized-badge/namer?period=total&units=international_system&left_color=grey&right_color=yellowgreen&left_text=Downloads
  :target: https://pepy.tech/project/namer  
.. image:: https://static.pepy.tech/personalized-badge/namer?period=month&units=international_system&left_color=grey&right_color=yellowgreen&left_text=Downloads/Month
  :target: https://pepy.tech/project/namer

Namer is a powerful command line tool and web app for renaming and tagging mp4 video files in a way that helps plex/jellyfin/emby and related plugins extract that data or lookup data with the PornDB_'s plugins for plex or jellyfin/emby.
Namer is easily installed as a python pip and can:

* can be used to name and embed tags in individual files with metadata from porndb:

  ``python -m namer rename -f /path/to/file/Site.[YY]YY.MM.DD.MessOfText.XXX.2160.mp4 [-v]`` 

* can be used to name and tag files with metadata from a jellyfin/emby/kodi .nfo file (should be named the same as the file except for extension).

  ``python -m namer rename -f /path/to/file/Site.[YY]YY.MM.DD.MessOfText.XXX.2160.mp4 -i [-v]``

* can be used to rename a tag a file based on the directory name, so if you have a file like ``/Site.[YY]YY.MM.DD.MessOfText.XXX.2160/abc.mp4`` 

  ``python -m namer rename -d /path/to/dir/Site.[YY]YY.MM.DD.MessOfText.XXX.2160/``

* can be used to rename a tag a whole mess of dirs and files in a directory (using -m, meaning "many").

  ``python -m namer rename -m -d /path/to/dir/``
  
* can be used to just suggest a possible name.  The file doesn't need to exist but should have an extension.

  ``python -m namer suggest -f Site.[YY]YY.MM.DD.MessOfText.XXX.2160.mp4``

* can be run watching a directory for new files to name, tag and move to an output location, possible setting file permissions, writing .nfo files with downloaded images, attempting to grab trailers, and retrying failed files nightly.

  ``python -m namer watchdog``  

* while running watchdog, will also have a webui that can be used to manually match and rename any failed files.  You can set the webroot, port, bound ip, enable/disable in the namer.cfg file.

  ``http:\\<ip>:6980\``

For all of the above it's recommended to have a config file in your home directory (copied from namer.cfg.sample in this git repo)

Also provided is a docker file if you prefer.

It is possible to ignore and not need to parse dates for studios added to a list in the configuration file.  This is mostly used for studios that do not list dates on videos.

Why should I use this?
----------------------

1.  You have partially well structured file names (say from an rss feed, etc) and you never want to have to manually match files in plex/jellyfin/emby with the PornDB_'s plugin.
2.  You don't want your recent videos to be added to your library until they are matchable in the PornDB_.
3.  You want to store the metadata about a file in mp4 files, in a way that can be read by Apple TV app, including information like: Studio, date created, name, performers, original url, proper HD tags, ratings, and movie poster.   All of this data is readable by Plex, and most by Jellyfin/Emby in case you want to standard Apple video players or your library's metadata storage is ever damaged.

How successful at matching videos is this tool?
------------------------------------------------

For data pulled from the internet with rss feeds (which are often in the file format listed below) .... perfect.  The author and others have only experienced one mismatch, and that type of failure can never occur again.

If running in a background watchdog mode, files that were failed to match are retried every 24 hours, letting the PornDB_ scrapers catch up with any metadata they may be missing.

Optionally, a log file can be enabled to show the original file name parts, what options were evaluated, and which match was used to name the file, it will be written next to your video file with the same name as the file (with a _namer.log) suffix rather than an mp4/mkv/avi/mov/flv extension.   This is very useful for sanity checking matches, and if ever a mismatch does occur the original file name is available in the log.


For the curious, how is a match made?
------------------------------------------------

It assumes that file names exist as in a format like ```sitename-[YY]YY-MM-DD-Scene.and.or.performer.name.mp4.```.  A powerful regex tries to determine the various parts of a file's name.   Note that the separating dashes and dots above are interchangeable, and spaces may also be used as separators (or any number of any combo of the three.)   This regex is overridable, but you really need to know what you're doing and if you don't have all the match groups for the regex, the match from the the PornDB_ will likely not be any where near as robust as it is with a site, a date, and a scene/perform name section.
You'll have to read the code to figure out how to set this.   You really shouldn't do it.

When determining a possible queried match from the PornDB_:

Sitename my not need be the full name of the site, as long as a the looked up sitename starts with file's sitename it could be a valid match.

The date may have a four digit or two digit year.  If two digit, "20" is assumed as the default century, not "19".  A potential match must be with one day plus/minus the file's date to be considered a match.

Finally the looked up scene name and all performers first and last names are combined in to what is called a powerset (every combo of including or not including each artist and/or scene name), and that is compared against the file's 'Scene.and.or.performer.name' section with a tool called rapidfuzz.   A name must be 90% similar to a member of the powerset to be considered a match, though all potential matches are evaluated and sorted before selecting the best match.   Information about all potential matches are stored in the local log file if it is enabled.

I'm sold how do I install it!
--------------------------------------------------

You have two choices.   Do you use docker?  Pull the docker image, here's docker-compose snippet to help you out.


.. code-block:: yaml

  version: "3"
  services:  
    namer:
      container_name: namer
      image: ghcr.io/theporndatabase/namer:latest
      environment:
        - PUID=1001
        - PGID=1000
        - TZ=America/Los_Angeles
        - NAMER_CONFIG=/config/namer.cfg
      volumes:
        - /apps/namer/:/config <- this will store the namer.cfg file.
        - /media:/data <- this will have the four folders namer needs to work, referenced in the config file.
      restart: always

Copy namer.cfg to your config location (a path mapped to /config/namer.cfg above), and set values for your setup.   
The config is well commented and you should only need to add a token for the porndb and change file locations.

Running a service will occur automatically once you call ``docker-compose up``.  Now check out the configuration section below.


Pip/Python usage
--------------------

What if you don't want to use docker and/or containers?  Do you have python 3 and pip (sometimes pip3) and the command line tool ``ffmpeg`` installed locally?  If so,  ``pip install namer`` gets the job done.  If
you don't have python (3), pip and ``ffmpeg`` installed Homebrew_ can help you on Mac, and Chocolatey_ can help you on windows


.. code-block:: sh

  # install namer
  pip3 install namer

  #optionallly, set your configuration location, the below is the default:
  export NAMER_CONFIG=${HOME}/.namer.cfg  

  # Run the watchdog service:
  python3 -m namer watchdog

  # Or manually rename a file, dir, or all sub-dirs/sub-files of a dir:
  # This calls the help method so that you can see the options.
  python3 -m namer rename -h


Configuration:
---------------------------

There is a well documented template of namer.cfg in this git repo, which is broken up in to three sections.
One section is related to command line renaming, the `namer section`_, one related to tagging mp4s `metadata section`_, 
and finally one related to the watchdog process `watchdog section`_.
Please note that the `namer section`_ section and the `watchdog section`_ 
section both have a field to describe the new name of a file based on looked up metadata from the PornDB_.   
They differ because when run from the command line namer will keep the file "in place".  
If namer is passed a dir on the command line as input it can operate in one of two modes,
the default mode is to look for the largest mp4 file, or other configured movie file extension if no mp4 exists,
and rename and move that file to the root of the folder (if it's in a sub-folder).
In this case, by default the assumption is the name of the folder should be parsed to look for information to
search the PornDB_ for matching rather than the file name.   Meaning,
if you pass a file to namer on the commandline it will be renamed but stay in the same directory.


Typical Watchdog Behavior:
----------------------------

The watchdog process will watch a single folder, configured with watch_dir_ in the ``namer.cfg`` file.   Any new files and directories that appear in the watch_dir_
will be processed once an mp4/mkv/avi/mov/flv file has been fully copied in to it.  

The first step in processing is to more the newly appearing directory or file in to the work_dir_.

Once moved the processing is highly dependant on the namer.cfg file, but in general, the name of video file or the directory file (configured with ``prefer_dir_name_if_available`` flag)
is parsed and matched with a scene from the PornDB_.   See `For the curious, how is a match made?`_.  If a match cannot be made the general assumption is that the PornDB_ doesn't have metadata for that file yet.
The file is move to the failed dir fail_dir_ to be retried once a day at a time configured with retry_time_,
which by default will be a random selected minute in the 3am hour of your timezone.   If enabled_tagging_ flag is set to true then
the metadata (including cover art if enable_poster_ is set) will be embedded in the mp4 file.  Please read the comments in the namer.cfg to find out about genres, tags, performers, etc.

Finally, the file is moved to a location defined by dest_dir_ and new_relative_path_name_.


Development
------------------------------

.. code-block:: sh

  # Install Python
  # Install poetry
  # Install poe the poet
  poetry self add 'poethepoet[poetry_plugin]'
  # or
  pip add poethepoet

  # Building:
  # install yarn deps
  yarn intall   

  # build css/js/copy templates
  yarn run build

  # install poetry dependencies
  poetry install

  # build python package in dist dir
  poetry build

  # Linting:
  poetry run flakeheaven lint

  # Testing:
  poetry run pytest

  # Formatting, maybe....:
  poetry run autopep8 --in-place namer/*.py test/*.py

  # Code Coverage:
  poetry run pytest --cov

  # Html Coverage report:
  poetry run coverage html

  # Local python install
  pip install ./dist/namer-<version>.tar.gz

  # Publishing:
  # First make sure you have set gotten a token from pypi and set it on your machine.
  poetry config pypi-token.pypi <token>

  # Perhaps update the version number?

  # Publishing a release to pypi.org:
  poetry publish

  # build docker file with:
  ./docker_build.sh

Pull Requests Are Welcome!
---------------------------

Just be sure to pay attention to the tests and any failing pylint results.   If you want to vet a pr will be accepted before building code, file an new feature request issue, and 4c0d3r will comment on it and set you up for success.   Tests are must.

.. _PornDB: http://metadataapi.net/
.. _namer section: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L1
.. _metadata section: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L59
.. _watchdog section: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L89
.. _watch_dir: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L100
.. _work_dir: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L104
.. _fail_dir: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L109
.. _dest_dir: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L112
.. _retry_time: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L115
.. _new_relative_path_name: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L97
.. _enabled_tagging: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L67
.. _enable_poster: https://github.com/ThePornDatabase/namer/blob/main/namer.cfg.sample#L72
.. _Homebrew: https://docs.brew.sh/Installation
.. _Chocolatey: https://chocolatey.org/install
