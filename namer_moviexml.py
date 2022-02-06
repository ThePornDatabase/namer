"""
Reads movie.xml of Emby/Jellyfin format in to a LookedUpFileInfo, allowing the metadata to be written in to video
files, or used in renaming the video file (currently only mp4s).
"""
import os
from lxml import objectify
from namer_types import LookedUpFileInfo, Performer


def readfile(file: str) -> str:
    """
    Utility function to read the contents of a file.
    """
    if os.path.isfile(file):
        with open(file, "r", encoding='utf_8') as text_file:
            data = text_file.read()
            text_file.close()
            return data
    return None


def parse_movie_xml_file(xmlfile: str) -> LookedUpFileInfo:
    """
    Parse an Emby/Jellyfin xml file and creates a LookedUpFileInfo from the data.
    """
    string = readfile(xmlfile)
    movie = objectify.fromstring(string)
    info = LookedUpFileInfo()
    info.name = str(movie.title)
    info.site = str(movie.studio[0])
    info.date = str(movie.releasedate)
    info.description = str(movie.plot)
    info.poster_url = str(movie.art.poster)
    info.performers = []
    for actor in movie.actor:
        performer = Performer()
        performer.name = str(actor.name)
        performer.role = str(actor.role)
        info.performers.append(performer)
    info.look_up_site_id = str(movie.phoenixadulturlid)
    info.uuid = str(movie.theporndbid)
    info.tags = []
    for genre in movie.genre:
        info.tags.append(str(genre))
    info.original_parsed_filename = None
    info.original_query = None
    info.origninal_response = None
    return info
