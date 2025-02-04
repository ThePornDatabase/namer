"""
This file can process individual movie files in place.
There name, or directory name, will be analyzed, matched against
the porndb, and used for renaming (in place), and updating a mp4
file's metadata (poster, artists, etc.)
"""
import argparse
import sys
from dataclasses import dataclass
import pathlib
import string
from pathlib import Path
from random import choices
from typing import List, Optional

from loguru import logger

from namer.command import Command
from namer.comparison_results import ComparisonResult, ComparisonResults, HashType, LookedUpFileInfo, SceneHash
from namer.configuration import ImageDownloadType, NamerConfig
from namer.configuration_utils import default_config, verify_configuration
from namer.command import make_command, move_command_files, move_to_final_location, set_permissions, write_log_file
from namer.database import search_file_in_database, write_file_to_database
from namer.ffmpeg import FFProbeResults, FFMpeg
from namer.fileinfo import FileInfo
from namer.metadataapi import get_complete_metadataapi_net_fileinfo, get_image, get_trailer, match, share_hash
from namer.moviexml import parse_movie_xml_file, write_nfo
from namer.name_formatter import PartialFormatter
from namer.mutagen import update_mp4_file
from namer.videophash import PerceptualHash, return_perceptual_hash

DESCRIPTION = """
    Namer, the porndb local file renamer. It can be a command line tool to rename mp4/mkv/avi/mov/flv files and to embed tags in mp4s,
    or a watchdog service to do the above watching a directory for new files and moving matched files to a target location.
    File names are assumed to be of the form SITE.[YY]YY.MM.DD.String.of.performers.and.or.scene.name.<IGNORED_INFO>.[mp4|mkv].
    In the name, read the periods, ".", as any number of spaces " ", dashes "-", or periods ".".

    Provided you have an access token to the porndb (free sign up) https://theporndb.net/, this program will
    attempt to match your file's name to search results from the porndb.   Please note that the site must at least be
    a substring of the actual site name on the porndb, and the date must be within one day or the release date on the
    porndb for a match to be considered.  If the log file flag is enabled then a <original file name minus ext>_namer.json.gz
    file will be written with all the potential matches sorted, descending by how closely the scene name/performer names
    match the file's name segment after the 'SITE.[YY]YY.MM.DD'.
  """


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class ProcessingResults:
    """
    Returned from the namer.py process() function.   It contains information about if a match
    was found, and of so, where files were placed.  It also tracks if a directory was inputted
    to namer (rather than the exact movie file.)  That knowledge can be used to move directories
    and preserve relative files, or to delete left over artifacts.
    """

    search_results: Optional[List[ComparisonResult]] = None
    """
    True if a match was found in the porndb.
    """

    new_metadata: Optional[LookedUpFileInfo] = None
    """
    New metadata found for the file being processed.
    Sourced including queries against the porndb, which would be stored in search_results,
    or reading a .nfo xml file next to the video, with the file name identical except for
    the extension, which would be .nfo instead of .mp4,.mkv,.avi,.mov,.flv.
    """

    dir_file: Optional[Path] = None
    """
    Set if the input file for naming was a directory.   This has advantages, as clean up of other files is now possible,
    or all files can be moved to a destination specified in the field final_name_relative.
    """

    video_file: Optional[Path] = None
    """
    The location of the found video file.
    """

    parsed_file: Optional[FileInfo] = None
    """
    The parsed file name.
    """

    final_name_relative: Optional[Path] = None
    """
    This is the full NamerConfig.new_relative_path_name string with all substitutions made.
    """


def dir_with_sub_dirs_to_process(dir_to_scan: Path, config: NamerConfig, infos: bool = False):
    """
    Used to find sub-dirs of a directory to be individually processed.
    The directories will be scanned for media and named/tagged in place
    based on config settings.
    """
    if dir_to_scan is not None and dir_to_scan.is_dir() and dir_to_scan.exists():
        logger.info('Scanning dir {} for sub-dirs/files to process', dir_to_scan)
        files = list(dir_to_scan.iterdir())
        files.sort()
        for file in files:
            fullpath_file = dir_to_scan / file
            if fullpath_file.is_dir() or fullpath_file.suffix.lower()[1:] in config.target_extensions:
                command = make_command(fullpath_file, config, nfo=infos, inplace=True)
                if command is not None:
                    process_file(command)


def tag_in_place(video: Optional[Path], config: NamerConfig, new_metadata: LookedUpFileInfo, ffprobe_results: Optional[FFProbeResults]):
    """
    Uses ComparisonResults to update a mp4 file's metadata based on a match in
    ComparisonResults.   Expects the first item of list to be the match if there is one.
    Will download a poster as well depending on NamerConfig config setting.
    """
    if new_metadata and video:
        poster = None
        if config.enabled_tagging and video.suffix.lower() == '.mp4':
            if config.enabled_poster:
                random = ''.join(choices(population=string.ascii_uppercase + string.digits, k=10))
                poster = get_image(new_metadata.poster_url, random, video, config) if new_metadata.poster_url else None

            logger.info('Updating file metadata (atoms): {}', video)
            update_mp4_file(video, new_metadata, poster, ffprobe_results, config)

        logger.info('Done tagging file: {}', video)
        if poster is not None and new_metadata.poster_url is not None and new_metadata.poster_url.startswith('http'):
            poster.unlink()


def get_local_metadata_if_requested(video_file: Path) -> Optional[LookedUpFileInfo]:
    """
    If there is an .nfo file next to the video_file, attempt to read it as
    an Emby/Jellyfin style movie xml file.
    """
    nfo_file = video_file.parent / (video_file.stem + '.nfo')
    if nfo_file.is_file() and nfo_file.exists():
        return parse_movie_xml_file(nfo_file)


def process_file(command: Command) -> Optional[Command]:
    """
    Bread and butter method.
    Given a file, determines if it's a dir, if so, the dir name may be used
    for comparison with the porndb.   The larges mp4/mkv file in the directory
    or any subdirectories will be assumed to be the movie file.

    Does not properly handle multipart movies.

    If the input file is not a dir it's name will be used, and it is assumed to
    be the movie file we wish to tag.

    The movie is either renamed in place if a file, or renamed and move to the root
    of the dir if a dir was passed in.

    The file is then update based on the metadata from the porndb if a mp4.
    """
    logger.info('Processing: {}', command.input_file)
    if command.target_movie_file is not None:
        phash: Optional[PerceptualHash] = None
        new_metadata: Optional[LookedUpFileInfo] = None
        search_results: ComparisonResults = ComparisonResults([], None)
        # convert container type if requested.
        if command.config.convert_container_to and command.target_movie_file.suffix != command.config.convert_container_to:
            new_loc = command.target_movie_file.parent.joinpath(Path(command.target_movie_file.stem + '.' + command.config.convert_container_to))
            if FFMpeg().convert(command.target_movie_file, new_loc):
                command.target_movie_file = new_loc
                if command.parsed_file:
                    command.parsed_file.extension = command.config.convert_container_to
        # Match to nfo files, if enabled and found.
        if command.write_from_nfos:
            new_metadata = get_local_metadata_if_requested(command.target_movie_file)
            if new_metadata is not None:
                new_metadata.original_parsed_filename = command.parsed_file
            else:
                logger.error('Could not process files: {}\nIn the file\'s name should start with a site, a date and end with an extension', command.input_file)
        # elif new_metadata is None and command.stashdb_id is not None and command.ff_probe_results is not None:
        #    phash = VideoPerceptualHash().get_phash(command.target_movie_file)
        #    todo use phash
        elif new_metadata is None and command.tpdb_id is not None and command.parsed_file is not None:
            file_infos = get_complete_metadataapi_net_fileinfo(command.parsed_file, command.tpdb_id, command.config)
            if file_infos is not None:
                new_metadata = file_infos
        elif new_metadata is None and ((command.parsed_file is not None and command.parsed_file.name is not None) or command.config.search_phash):
            phash = calculate_phash(command.target_movie_file, command.config) if command.config.search_phash else None
            if phash:
                logger.info(f'Calculated hashes: {phash.to_dict()}')
                command.parsed_file.hashes = phash

            search_results = match(command.parsed_file, command.config, phash=phash)
            if search_results:
                matched = search_results.get_match()
                if matched:
                    new_metadata = matched.looked_up

            if not command.target_movie_file:
                logger.error(
                    """
                    Could not process file or directory: {}
                    Likely attempted to use the directory's name as the name to parse.
                    In general the dir or file's name should start with a site, a date and end with an extension
                    Target video file in dir was: {}""",
                    command.input_file,
                    command.target_movie_file,
                )

        target_dir = command.target_directory if command.target_directory is not None else command.target_movie_file.parent
        set_permissions(target_dir, command.config)
        if new_metadata is not None:
            if command.config.manual_mode and command.is_auto:
                failed = move_command_files(command, command.config.failed_dir)
                if failed is not None and search_results is not None and failed.config.write_namer_failed_log:
                    write_log_file(failed.target_movie_file, search_results, failed.config)
            else:
                ffprobe_results = command.config.ffmpeg.ffprobe(command.target_movie_file)
                if ffprobe_results:
                    new_metadata.resolution = ffprobe_results.get_resolution()

                    video = ffprobe_results.get_default_video_stream()
                    new_metadata.video_codec = video.codec_name if video else None

                    audio = ffprobe_results.get_default_audio_stream()
                    new_metadata.audio_codec = audio.codec_name if audio else None

                if command.config.send_phash:
                    phash = phash if phash else calculate_phash(command.target_movie_file, command.config)
                    if phash:
                        command.parsed_file.hashes = phash

                        scene_hash = SceneHash(str(phash.phash), HashType.PHASH, phash.duration)
                        share_hash(new_metadata, scene_hash, command.config)

                        scene_hash = SceneHash(phash.oshash, HashType.OSHASH, phash.duration)
                        share_hash(new_metadata, scene_hash, command.config)

                log_file = command.config.failed_dir / (command.input_file.stem + '_namer.json.gz')
                if log_file.is_file():
                    log_file.unlink()

                target = move_to_final_location(command, new_metadata)
                tag_in_place(target.target_movie_file, command.config, new_metadata, ffprobe_results)
                add_extra_artifacts(target.target_movie_file, new_metadata, search_results, phash, command.config)

                logger.success('Done processing file: {}, moved to {}', command.target_movie_file, target.target_movie_file)
                return target
        elif command.inplace is False:
            failed = move_command_files(command, command.config.failed_dir)
            if failed is not None and search_results is not None and failed.config.write_namer_failed_log:
                write_log_file(failed.target_movie_file, search_results, failed.config)


def add_extra_artifacts(video_file: Path, new_metadata: LookedUpFileInfo, search_results: ComparisonResults, phash: Optional[PerceptualHash], config: NamerConfig):
    """
    Once the file is in its final location we will grab other relevant output if requested.
    """
    if config.write_namer_log:
        write_log_file(video_file, search_results, config)

    trailer = None
    if config.trailer_location and new_metadata:
        trailer = get_trailer(new_metadata.trailer_url, video_file, config)

    if new_metadata:
        poster = get_image(new_metadata.poster_url, '-poster', video_file, config) if new_metadata.poster_url and config.enabled_poster and ImageDownloadType.POSTER in config.download_type else None
        background = get_image(new_metadata.background_url, '-background', video_file, config) if new_metadata.background_url and config.enabled_poster and ImageDownloadType.BACKGROUND in config.download_type else None
        for performer in new_metadata.performers:
            if isinstance(performer.image, str):
                performer_image = get_image(performer.image, '-Performer-' + performer.name.replace(' ', '-') + '-image', video_file, config) if performer.image and config.enabled_poster and ImageDownloadType.PERFORMER in config.download_type else None
                if performer_image:
                    performer.image = performer_image

        if config.write_nfo:
            write_nfo(video_file, new_metadata, config, trailer, poster, background, phash)


def check_arguments(file_to_process: Path, dir_to_process: Path, config_override: Path):
    """
    check arguments.
    """
    error = False
    if file_to_process is not None:
        logger.info('File to process: {}', file_to_process)
        if not file_to_process.is_file() or not file_to_process.exists():
            logger.error('Error not a file! {}', file_to_process)
            error = True

    if dir_to_process is not None:
        logger.info('Directory to process: {}', dir_to_process)
        if not dir_to_process.is_dir() or not dir_to_process.exists():
            logger.error('Error not a directory! {}', dir_to_process)
            error = True

    if config_override is not None:
        logger.info('Config override specified: {}', config_override)
        if not config_override.is_file() or not config_override.exists():
            logger.warning('Config override specified, but file does not exit: {}', config_override)
            error = True

    return error


def calculate_phash(file: Path, config: NamerConfig) -> Optional[PerceptualHash]:
    if config.use_database:
        search_result = search_file_in_database(file)
        if search_result:
            logger.info(f'Getting phash from db for file "{file}"')
            return return_perceptual_hash(search_result.duration, search_result.phash, search_result.oshash)

    vph = config.vph_alt if config.use_alt_phash_tool else config.vph
    phash = vph.get_hashes(file, max_workers=config.max_ffmpeg_workers, use_gpu=config.use_gpu if config.use_gpu else False)

    if phash and config.use_database:
        write_file_to_database(file, phash)

    return phash


def main(arg_list: List[str]):
    """
    Used to tag and rename files from the command line.
    See usage function above.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('-c', '--configfile', type=pathlib.Path, help='config file, defaults first to env var NAMER_CONFIG, then local path namer.cfg, and finally ~/.namer.cfg.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', type=Path, help='a single file to process, and rename.')
    group.add_argument('-d', '--dir', type=Path, help='a directory to process.')
    parser.add_argument('-m', '--many', action='store_true', help="if set, a directory have all it's sub directories processed. Files move only within sub dirs, or are renamed in place, if in the root dir to scan")
    parser.add_argument(
        '-i',
        '--infos',
        action='store_true',
        help='if set, .nfo files will attempt to be accessed next to movie files, if info files are found and parsed successfully, that metadata will be used rather than porndb matching. If using jellyfin .nfo files, please bump your release date by one day until they fix this issue: https://github.com/jellyfin/jellyfin/issues/7271.',
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose, print logs')
    args = parser.parse_args(arg_list)
    check_arguments(args.file, args.dir, args.configfile)

    conf: Optional[Path] = args.configfile
    config: NamerConfig = default_config(conf)

    if args.verbose:
        level = 'DEBUG' if config.debug else 'INFO'
        logger.add(sys.stdout, format=config.console_format, level=level, diagnose=config.diagnose_errors)

    verify_configuration(config, PartialFormatter())

    target = args.file
    if args.dir is not None:
        target = args.dir

    if args.many:
        dir_with_sub_dirs_to_process(args.dir.absolute(), config, args.infos)
    else:
        command = make_command(target.absolute(), config, inplace=True, nfo=args.infos)
        if command is not None:
            process_file(command)
