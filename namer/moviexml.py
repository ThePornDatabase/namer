"""
Reads movie.xml (your.movie.name.nfo) of Emby/Jellyfin format in to a LookedUpFileInfo,
allowing the metadata to be written in to video files (currently only mp4's),
or used in renaming the video file.
"""
import re
from pathlib import Path

from typing import Any, Optional, List
from xml.dom.minidom import parseString, Document, Element

from namer.configuration import NamerConfig
from namer.command import set_permissions
from namer.comparison_results import LookedUpFileInfo, Performer
from namer.videophash import PerceptualHash


def get_childnode(node: Element, name: str) -> Element:
    return node.getElementsByTagName(name)[0]


def get_all_childnode(node: Element, name: str) -> List[Element]:
    return node.getElementsByTagName(name)


def get_childnode_text(node: Element, name: str) -> str:
    return node.getElementsByTagName(name)[0].childNodes[0].data


def get_all_childnode_text(node: Element, name: str) -> List[str]:
    return [x.childNodes[0].data for x in node.getElementsByTagName(name)]


def parse_movie_xml_file(xml_file: Path) -> LookedUpFileInfo:
    """
    Parse an Emby/Jellyfin xml file and creates a LookedUpFileInfo from the data.
    """
    content = xml_file.read_text(encoding="UTF-8")

    movie: Any = parseString(bytes(content, encoding="UTF-8"))
    info = LookedUpFileInfo()
    info.name = get_childnode_text(movie, 'title')
    info.site = get_all_childnode_text(movie, 'studio')[0]
    info.date = get_childnode_text(movie, 'releasedate')
    info.description = get_childnode_text(movie, 'plot')
    art = get_childnode(movie, 'art')
    info.poster_url = get_childnode_text(art, 'poster')

    info.performers = []
    for actor in get_all_childnode(movie, "actor"):
        name = get_childnode_text(actor, 'name')
        if actor and name:
            performer = Performer(name)
            performer.role = get_childnode_text(actor, 'role')
            info.performers.append(performer)

    phoenixadulturlid = get_childnode_text(movie, 'phoenixadulturlid')
    if phoenixadulturlid:
        info.look_up_site_id = phoenixadulturlid

    theporndbid = get_childnode_text(movie, 'theporndbid')
    if theporndbid:
        info.uuid = theporndbid

    info.tags = []
    for genre in get_all_childnode_text(movie, "genre"):
        info.tags.append(str(genre))

    info.original_parsed_filename = None
    info.original_query = None
    info.original_response = None

    return info


def add_sub_element(doc: Document, parent: Element, name: str, text: Optional[str] = None) -> Element:
    sub_element = doc.createElement(name)
    parent.appendChild(sub_element)

    if text:
        txt_node = doc.createTextNode(text)
        sub_element.appendChild(txt_node)

    return sub_element


def add_all_sub_element(doc: Document, parent: Element, name: str, text_list: List[str]) -> None:
    if text_list:
        for text in text_list:
            sub_element = doc.createElement(name)
            parent.appendChild(sub_element)
            txt_node = doc.createTextNode(text)
            sub_element.appendChild(txt_node)


def write_movie_xml_file(info: LookedUpFileInfo, config: NamerConfig, trailer: Optional[Path] = None, poster: Optional[Path] = None, background: Optional[Path] = None, phash: Optional[PerceptualHash] = None) -> str:
    """
    Parse porndb info and create an Emby/Jellyfin xml file from the data.
    """
    doc = Document()
    root: Element = doc.createElement('movie')
    doc.appendChild(root)
    add_sub_element(doc, root, "plot", info.description)
    add_sub_element(doc, root, "outline")
    add_sub_element(doc, root, "title", info.name)
    add_sub_element(doc, root, "dateadded")
    add_sub_element(doc, root, "trailer", str(trailer) if trailer else None)
    add_sub_element(doc, root, "year", info.date[:4] if info.date else None)
    add_sub_element(doc, root, "premiered", info.date)
    add_sub_element(doc, root, "releasedate", info.date)
    add_sub_element(doc, root, "mpaa", "XXX")

    art = add_sub_element(doc, root, "art")

    poster_match = re.search(r'.*/(.*)', str(poster)) if poster else None
    add_sub_element(doc, art, 'poster', poster_match.group(1) if poster_match else None)
    background_match = re.search(r'.*/(.*)', str(background)) if background else None
    add_sub_element(doc, art, 'background', background_match.group(1) if background_match else None)

    if config.enable_metadataapi_genres:
        add_all_sub_element(doc, root, 'genre', info.tags)
    else:
        add_all_sub_element(doc, root, 'tag', info.tags)
        add_sub_element(doc, root, 'genre', config.default_genre)

    add_sub_element(doc, root, 'studio', info.site)
    add_sub_element(doc, root, 'theporndbid', str(info.uuid))
    add_sub_element(doc, root, 'theporndbguid', str(info.guid))
    add_sub_element(doc, root, 'phoenixadultid')
    add_sub_element(doc, root, 'phoenixadulturlid')

    add_sub_element(doc, root, 'phash', str(phash.phash) if phash else '')
    add_sub_element(doc, root, 'sourceid', info.source_url)

    for performer in info.performers:
        actor = add_sub_element(doc, root, 'actor')
        add_sub_element(doc, actor, 'name', performer.name)
        add_sub_element(doc, actor, 'role', performer.role)
        performer_match = re.search(r'.*/(.*)', str(performer.image)) if performer.image else None
        add_sub_element(doc, actor, 'image', performer_match.group(1) if performer_match else None)
        add_sub_element(doc, actor, 'type', "Actor")
        add_sub_element(doc, actor, 'thumb')

    add_sub_element(doc, root, 'fileinfo')

    return str(doc.toprettyxml(indent="  ", newl='\n', encoding="UTF-8"), encoding="UTF-8")


def write_nfo(video_file: Path, new_metadata: LookedUpFileInfo, namer_config: NamerConfig, trailer: Optional[Path], poster: Optional[Path], background: Optional[Path], phash: Optional[PerceptualHash]):
    """
    Writes an .nfo to the correct place for a video file.
    """
    if video_file and new_metadata and namer_config.write_nfo:
        target = video_file.parent / (video_file.stem + ".nfo")
        with open(target, "wt", encoding="UTF-8") as nfo_file:
            towrite = write_movie_xml_file(new_metadata, namer_config, trailer, poster, background, phash)
            nfo_file.write(towrite)

        set_permissions(target, namer_config)
