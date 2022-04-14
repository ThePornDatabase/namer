"""
Reads movie.xml (your.movie.name.nfo) of Emby/Jellyfin format in to a LookedUpFileInfo,
allowing the metadata to be written in to video files (currently only mp4s),
or used in renaming the video file.
"""
from pathlib import Path
from lxml import objectify, etree
from namer.types import LookedUpFileInfo, NamerConfig, Performer, set_permissions

def parse_movie_xml_file(xmlfile: Path) -> LookedUpFileInfo:
    """
    Parse an Emby/Jellyfin xml file and creates a LookedUpFileInfo from the data.
    """
    content = xmlfile.read_text(encoding="utf8")

    movie = objectify.fromstring(bytes(content, encoding="utf8"))
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
    if hasattr(movie, "phoenixadulturlid"):
        info.look_up_site_id = str(movie.phoenixadulturlid)
    if hasattr(movie, "theporndbid"):
        info.uuid = str(movie.theporndbid)
    info.tags = []
    for genre in movie.genre:
        info.tags.append(str(genre))
    info.original_parsed_filename = None
    info.original_query = None
    info.origninal_response = None
    return info


def write_movie_xml_file(info: LookedUpFileInfo) -> str:
    """
    Parse porndb info and create an Emby/Jellyfin xml file from the data.
    """
    element_maker = objectify.ElementMaker(annotate=False)

    root = element_maker("movie")
    root["plot"]=info.description
    root["outline"] =  None
    root["title"] = info.name
    root["dateadded"] =  None
    root["trailer"] =  None
    root["year"] = info.date[:4]
    root["mpaa"] = "XXX"
    root["premiered"] = info.date
    root["releasedate"] = info.date
    root["runtime"] =  None
    root["root"] =  None
    root["root"]["art"] =  None
    #(
    #         element_maker.poster(),
    #         element_maker.fanart(),
    #     ),
    # )

    for genre in info.tags:
        genre_tag = objectify.SubElement(root, "genre")
        genre_tag["text"] = genre

    objectify.SubElement(root, "theporndbid")["text"]=(f'{info.uuid}')
    objectify.SubElement(root, "phoenixadultid")
    objectify.SubElement(root, "phoenixadulturlid")

    for performer in info.performers:
        actor = objectify.SubElement(root, "actor")
        objectify.SubElement(actor, "name")["text"] = (performer.name)
        objectify.SubElement(actor, "role")["text"] = (performer.role)
        objectify.SubElement(actor, "type")["text"] = ("Actor")
        objectify.SubElement(actor, "thumb")

    objectify.SubElement(root, "fileinfo")

    objectify.deannotate(root)
    etree.cleanup_namespaces(root)
    return str(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

def write_nfo(video_file: Path, info: LookedUpFileInfo, namer_config: NamerConfig ) -> Path:
    """
    Writes an .nfo to the correct place for a video file.
    """
    if video_file is not None and info is not None and namer_config.write_nfo is True:
        target = video_file.parent / (video_file.stem + ".nfo")
        target.write_text(write_movie_xml_file(info))
        set_permissions(target, namer_config)
