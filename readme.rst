Namer
#########

.. image:: https://github.com/4c0d3r/namer/actions/workflows/ci.yml/badge.svg?
  :target: https://github.com/4c0d3r/namer/actions/workflows/ci.yml/
.. image:: https://codecov.io/gh/4c0d3r/namer/branch/main/graph/badge.svg?token=4MQEN2NUKZ
  :target: https://codecov.io/gh/4c0d3r/namer
.. image:: https://badge.fury.io/py/namer.svg?
  :target: https://badge.fury.io/py/namer  

Namer is a powerful command line tool for renaming and tagging mp4 video files in a way that helps plex/jellyfin/emby and related plugins extract that data or lookup data with the PornDB_'s plugins for plex or jellyfin/emby.

Why should I use this?
----------------------

1.  You have partially well structured file names (say from an rss feed, etc) and you never want to have to manually match files in plex/jellyfin/emby with the PornDB_'s plugin.
2.  You don't want your recent videos to be added to your library until they are matchable in the PornDB_.
3.  You want to store the metadata about a file in mp4 files, in a way that can be read by Apple TV app, including information like: Studio, date created, name, performers, original url, proper HD tags, ratings, and movie poster.   All of this data is readable by Plex, and most by Jellyfin/Emby in case you want to standard Apple video players or your library's metadata storage is ever damaged.

How successful at matching videos is this tool?
------------------------------------------------

For data pulled from the intered with rss feeds (which are often in the file format listed below) .... perfect.  The author and others have only experienced one mismatch, and that type of failure can never occur again.   

If running in a background watchdog mode, files that were failed to match are retried every 24 hours, letting the PornDB_ scrapers catch up with any metadata they may be missing.

Optionally, a log file can be enabled to show the original file name parts, what options were evaluated, and which match was used to name the file, it will be written next to your video file with the same name as the file (with a _namer.log) suffix rather than an mp4/mkv extension.   This is very useful for sanity checking matches, and if ever a mismatch does occur the original file name is available in the log.


For the curious, how is a match made?
------------------------------------------------

It assumes that file names exist as in a format like ```sitename-[YY]YY-MM-DD-Scene.and.or.performer.name.mp4.```.  A power regex tries to determine the various parts of a file's name.   Note that the seperating dashes and dots above are interchangable, and spaces may also be used as seperators (or any number of any combo of the three.) 

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
      image: porndb/namer:latest
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
The config is well commented.

Running a service will occur automatically once you call ``docker-compose up``.  Now check out the configuration section below.


Pip/Python usage
--------------------

What if you don't want to use docker and/or containers?  Do you have python 3 and pip (sometimes pip3) and the command line tool ``ffmpeg`` installed locally?  If so,  ``pip install namer`` get's the job done.  If
you don't have python (3), pip and ``ffmpeg`` installed Homebrew_ can help you on Mac, and Chocolatey_ can help you on windows


.. code-block:: sh

  # install namer
  pip3 install namer

  #optionallly, set your configuration location, the below is the default:
  export NAMER_CONFIG=${HOME}/.namer.cfg  

  # Run the watchdog service:
  python3 -m namer watchdog

  # Or manually rename a file, dir, or all subdirs/subfiles of a dir:
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
If namer is passed a dir on the command line as input it can opperate in one of two modes,
the default mode is to look for the largest mp4 file, or mkv if no mp4 exists,
and rename and move that file to the root of the folder (if it's in a subfolder).
In this case, by default the assumption is the name of the folder should be parsed to look for information to
search the PornDB_ for matching rather than the file name.   Meaning,
if you pass a file to namer on the commandline it will be renamed but stay in the same directory.


Typical Watchdog Behavior:
----------------------------

The watchdog process will watch a single folder, configured with watch_dir_ in the ``namer.cfg`` file.   Any new files and directories that appear in the watch_dir_
will be processed once an mp4/mkv file has been fully copied in to it.  

The first step in processing is to moce the newly appearing directory or file in to the work_dir_.  

Once moved the processing is highly dependant on the namer.cfg file, but in general, the name of video file or the directory file (configured with ``prefer_dir_name_if_available`` flag)
is parsed and matched with a scene from the PornDB_.   See `For the curious, how is a match made?`_.  If a match cannot be made the general assumption is that the PornDB_ doesn't have metadata for that file yet.
The file is move to the failed dir fail_dir_ to be retried once a day at a time configured with retry_time_,
which by default will be a random selected minute in the 3am hour of your timezone.   If enabled_tagging_ flag is set to true then
the metadata (including cover art if enable_poster_ is set) will be embedded in the mp4 file.  Please read the comments in the namer.cfg to find out about genres, tags, performers, etc.

Finally, the file is movied to a location defined by dest_dir_ and new_relative_path_name_.


Development
------------------------------

.. code-block:: sh

  # Building:
  poetry build

  # Linting:
  poetry run pylint namer

  # Testing:
  poetry run pytest

  # Code Coverage:
  poetry run pytest --cov

  # Html Coverage report:
  poetry run coverage html

  # Publishing:
  # First make sure you have set gotten a token from pypi and set it on your machine.
  poetry config pypi-token.pypi <token>

  # Perhaps update the version number?

  # Publishing a release to pypi.org:
  poetry publish

  # build docker file with:
  ./docker_build.sh


.. _PornDB: http://metadataapi.net/
.. _namer section: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L1
.. _metadata section: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L59
.. _watchdog section: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L89
.. _watch_dir: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L100
.. _work_dir: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L104
.. _fail_dir: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L109
.. _dest_dir: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L112
.. _retry_time: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L115
.. _new_relative_path_name: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L97
.. _enabled_tagging: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L67
.. _enable_poster: https://github.com/4c0d3r/namer/blob/main/namer.cfg#L72
.. _Homebrew: https://docs.brew.sh/Installation
.. _Chocolatey: https://chocolatey.org/install