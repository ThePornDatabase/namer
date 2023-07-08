from pony.orm import Optional, PrimaryKey, Required

from namer.models import db


class File(db.Entity):
    id = PrimaryKey(int, auto=True)

    file_name = Required(str)
    file_size = Required(int, size=64)
    file_time = Required(float)

    duration = Optional(int)
    phash = Optional(str)
    oshash = Optional(str)
