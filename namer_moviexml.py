"""
Reads movie.xml (your.movie.name.nfo) of Emby/Jellyfin format in to a LookedUpFileInfo, 
allowing the metadata to be written in to video files (currently only mp4s),
or used in renaming the video file.
"""
from pathlib import Path
from lxml import objectify
from namer_types import LookedUpFileInfo, Performer

def parse_movie_xml_file(xmlfile: Path) -> LookedUpFileInfo:
    """
    Parse an Emby/Jellyfin xml file and creates a LookedUpFileInfo from the data.
    """
    content = xmlfile.read_text(encoding="utf_8")

    movie = objectify.fromstring(content)
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
