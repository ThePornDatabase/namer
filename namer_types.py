from dataclasses import dataclass
from typing import List

@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FileNameParts:
    """
    Represents info parsed from a file name, usually of an nzb, named something like:
    'EvilAngel.22.01.03.Carmela.Clutch.Fabulous.Anal.3-Way.XXX.2160p.MP4-GAYME-xpost'
    or
    'DorcelClub.20.12..Aya.Benetti.Megane.Lopez.And.Bella.Tina.2160p.MP4-GAYME-xpost'
    """
    site: str = ""
    """
    Site the file originated from, "DorcelClub", "EvilAngel", etc.
    """
    date: str = ""
    """
    formated: YYYY-mm-dd 
    """
    name: str = ""
    act: str = ""
    """
    If the name originally ended with an "act ###" or "part ###"
    it will be stripped out and placed in a seperate location, aids in matching.
    """
    extension: str = ""
    """
    The file's extension (always .mp4)
    """
    resolution: str = ""
    """
    Resolution, if the file name makes a claim about resolution. (480p, 720p, 1080p, 4k)
    """
    source_file_name: str = ""
    """
    What was originally parsed.
    """

@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class Performer:
    """
    Minimal info about a perform, name, and role.
    """
    name: str
    role: str
    """
    if available the performers gender, stored as a role.  example: "Female", "Male"
    Useful as many nzbs often don't include the scene name, but instead female performers names,
    or sometimes both.
    Other performers are also used in name matching, if females are attempted first.
    """

    def __init__(self, name=None, role=None):
        self.name = name
        self.role = role

    # def __eq__(self, other):
    #     if isinstance(other, self.__class__):
    #         return self.__dict__ == other.__dict__
    #     else:
    #         return False

    # def __ne__(self, other):
    #     return not self.__eq__(other)

    # def __hash__(self):
    #     return hash((self.name, self.role)) 

    def __str__(self):
        if self.role != None:
            return self.name + " (" + self.role + ")" 
        else:
            return self.name 

    def __repr__(self):
        return 'Performer[name=' + self.name + ', role=%s' % self.role +']'


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class LookedUpFileInfo():
    site: str = ""
    """
    Site where this video originated, DorcelClub/Deeper/etc.....
    """
    date: str = ""
    """
    date of initial release, formated YYYY-mm-dd 
    """
    name: str = ""
    """
    Name of the scene in this video
    """
    description: str = ""
    """
    Description of the action in this video
    """
    source_url: str = ""
    """
    Original source location of this video
    """
    poster_url: str = ""
    """
    Url to download a poster for this video
    """
    performers: List[Performer]
    """
    List of performers, containing names, and "roles" aka genders, for each performer.
    """
    origninal_response: str = ""
    """
    json reponse parsed in to this object.
    """
    original_query: str = ""
    """
    url query used to get the above json response
    """
    original_parsed_filename: FileNameParts
    """
    The FileNameParts used to build the orignal_query
    """
    look_up_site_id: str = ""
    """
    ID Used by the queried site to identify the video
    """
    def __init__(self):
        self.performers = []
    
    def new_file_name(self):
        return (self.original_parsed_filename.site 
                + " - " + 
                self.original_parsed_filename.date 
                + " - " + 
                self.name
                + "." + 
                self.original_parsed_filename.extension.lower())