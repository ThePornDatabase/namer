"""
Reads movie.xml (your.movie.name.nfo) of Emby/Jellyfin format in to a LookedUpFileInfo,
allowing the metadata to be written in to video files (currently only mp4s),
or used in renaming the video file.
"""
from pathlib import Path
from typing import Any, Optional
from lxml import objectify, etree
from namer.types import (
    LookedUpFileInfo,
    NamerConfig,
    Performer,
    ProcessingResults,
    set_permissions,
)


def parse_movie_xml_file(xmlfile: Path) -> LookedUpFileInfo:
    """
    Parse an Emby/Jellyfin xml file and creates a LookedUpFileInfo from the data.
    """
    content = xmlfile.read_text(encoding="utf8")

    movie: Any = objectify.fromstring(bytes(content, encoding="utf8"), parser=None)
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


def write_movie_xml_file(
    info: LookedUpFileInfo,
    config: NamerConfig,
    trailer: Optional[Path] = None,
    poster: Optional[Path] = None,
    background: Optional[Path] = None,
) -> str:
    """
    Parse porndb info and create an Emby/Jellyfin xml file from the data.
    """

    root: Any = etree.Element("movie", attrib=None, nsmap=None)
    etree.SubElement(root, "plot", attrib=None, nsmap=None).text = info.description
    etree.SubElement(root, "outline", attrib=None, nsmap=None)
    etree.SubElement(root, "title", attrib=None, nsmap=None).text = info.name
    etree.SubElement(root, "dateadded", attrib=None, nsmap=None)
    trailertag = etree.SubElement(root, "trailer", attrib=None, nsmap=None)
    if trailer is not None:
        trailertag.text = str(trailer)
    if info.date is not None:
        etree.SubElement(root, "year", attrib=None, nsmap=None).text = info.date[:4]
    etree.SubElement(root, "premiered", attrib=None, nsmap=None).text = info.date
    etree.SubElement(root, "releasedate", attrib=None, nsmap=None).text = info.date
    etree.SubElement(root, "mpaa", attrib=None, nsmap=None).text = "XXX"
    art = etree.SubElement(root, "art", attrib=None, nsmap=None)
    postertag = etree.SubElement(art, "poster", attrib=None, nsmap=None)
    if poster is not None:
        postertag.text = str(poster)
    backgroundtag = etree.SubElement(art, "background", attrib=None, nsmap=None)
    if background is not None:
        backgroundtag.text = str(background)
    if config.enable_metadataapi_genres:
        for tag in info.tags:
            etree.SubElement(root, "genre", attrib=None, nsmap=None).text = tag
    else:
        for tag in info.tags:
            etree.SubElement(root, "tag", attrib=None, nsmap=None).text = tag
        etree.SubElement(root, "genre", attrib=None, nsmap=None).text = config.default_genre
    etree.SubElement(root, "studio", attrib=None, nsmap=None).text = info.site
    etree.SubElement(root, "theporndbid", attrib=None, nsmap=None).text = str(info.uuid)
    etree.SubElement(root, "phoenixadultid", attrib=None, nsmap=None)
    etree.SubElement(root, "phoenixadulturlid", attrib=None, nsmap=None)
    etree.SubElement(root, "sourceid", attrib=None, nsmap=None).text = info.source_url
    for performer in info.performers:
        actor = objectify.SubElement(root, "actor", attrib=None, nsmap=None)
        etree.SubElement(actor, "name", attrib=None, nsmap=None).text = performer.name
        etree.SubElement(actor, "role", attrib=None, nsmap=None).text = performer.role
        etree.SubElement(actor, "image", attrib=None, nsmap=None).text = str(performer.image)
        etree.SubElement(actor, "type", attrib=None, nsmap=None).text = "Actor"
        etree.SubElement(actor, "thumb", attrib=None, nsmap=None)
    objectify.SubElement(root, "fileinfo", attrib=None, nsmap=None)
    objectify.deannotate(root)
    etree.cleanup_namespaces(root, top_nsmap=None, keep_ns_prefixes=None)
    return etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"  # type: ignore
    ).decode(encoding="UTF-8")


def write_nfo(
    results: ProcessingResults,
    namer_config: NamerConfig,
    trailer: Optional[Path],
    poster: Optional[Path],
    background: Optional[Path],
):
    """
    Writes an .nfo to the correct place for a video file.
    """
    if results.video_file is not None and results.new_metadata is not None and namer_config.write_nfo is True:
        target = results.video_file.parent / (results.video_file.stem + ".nfo")
        with open(target, "wt", encoding="utf-8") as nfofile:
            towrite = write_movie_xml_file(results.new_metadata, namer_config, trailer, poster, background)
            nfofile.write(towrite)
        set_permissions(target, namer_config)
