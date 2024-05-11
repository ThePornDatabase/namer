import re
import string

from jinja2 import Template
from jinja2.filters import FILTERS


class PartialFormatter(string.Formatter):
    """
    Used for formatting NamerConfig.inplace_name and NamerConfig.
    """

    supported_keys = [
        'date',
        'description',
        'name',
        'site',
        'full_site',
        'parent',
        'full_parent',
        'network',
        'full_network',
        'performers',
        'all_performers',
        'act',
        'ext',
        'trans',
        'uuid',
        'vr',
        'type',
        'year',
        'resolution',
        'video_codec',
        'audio_codec',
        'external_id',
    ]

    __regex = {
        's': re.compile(r'.\d+s'),
        'p': re.compile(r'.\d+p'),
        'i': re.compile(r'.\d+i'),
    }

    def __init__(self, missing='~~', bad_fmt='!!'):
        self.missing, self.bad_fmt = missing, bad_fmt
        FILTERS['split'] = str.split

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val = super().get_field(field_name, args, kwargs)
        except (KeyError, AttributeError) as err:
            val = None, field_name
            if field_name not in self.supported_keys:
                raise KeyError(f'Key {field_name} not in support keys: {self.supported_keys}') from err

        return val

    def format_field(self, value, format_spec: str):
        if not value:
            return self.missing

        try:
            if self.__regex['s'].match(format_spec):
                value = value + format_spec[0] * int(format_spec[1:-1])
                format_spec = ''
            elif self.__regex['p'].match(format_spec):
                value = format_spec[0] * int(format_spec[1:-1]) + value
                format_spec = ''
            elif self.__regex['i'].match(format_spec):
                value = format_spec[0] * int(format_spec[1:-1]) + value + format_spec[0] * int(format_spec[1:-1])
                format_spec = ''
            elif format_spec.startswith('|'):
                template = Template(f'{{{{ val{format_spec} }}}}')
                value = template.render(val=value)
                format_spec = ''

            return super().format_field(value, format_spec)
        except ValueError:
            if self.bad_fmt:
                return self.bad_fmt
            raise
