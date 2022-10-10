import re
import string
from typing import Tuple


class PartialFormatter(string.Formatter):
    """
    Used for formatting NamerConfig.inplace_name and NamerConfig.
    """

    __supported_keys = [
        "date",
        "description",
        "name",
        "site",
        "full_site",
        "performers",
        "all_performers",
        "act",
        "ext",
        "trans",
        "uuid",
        "vr",
        "type",
        "resolution",
        "external_id",
    ]

    __functions = {
        'lower': str.lower,
        'upper': str.upper,
        'title': str.title,
        'replace': str.replace,
    }

    def __init__(self, missing="~~", bad_fmt="!!"):
        self.missing, self.bad_fmt = missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            field_name, mods = field_name.split('|', 1) if '|' in field_name else (field_name, '')
            val = super().get_field(field_name, args, kwargs)
            val = self.__apply_mods(val, mods)

        except (KeyError, AttributeError) as err:
            val = None, field_name
            if field_name not in self.__supported_keys:
                raise KeyError(f"Key {field_name} not in support keys: {self.__supported_keys}") from err

        return val

    def format_field(self, value, format_spec: str):
        if not value:
            return self.missing
        try:
            if re.match(r".\d+s", format_spec):
                value = value + format_spec[0] * int(format_spec[1:-1])
                format_spec = ""
            if re.match(r".\d+p", format_spec):
                value = format_spec[0] * int(format_spec[1:-1]) + value
                format_spec = ""
            if re.match(r".\d+i", format_spec):
                value = format_spec[0] * int(format_spec[1:-1]) + value + format_spec[0] * int(format_spec[1:-1])
                format_spec = ""
            return super().format_field(value, format_spec)
        except ValueError:
            if self.bad_fmt:
                return self.bad_fmt
            raise

    def __apply_mods(self, val: Tuple[str, str], mods: str) -> Tuple[str, str]:
        res, key = val

        for mod in mods.split('|'):
            mod_args = []
            if '(' in mod and ')' in mod:
                mod, mod_args = mod.split('(', 1)
                mod_args = mod_args.split(')', 1)[0]
                mod_args = mod_args.split(',')

            if mod in self.__functions:
                func = self.__functions[mod]
                res = func(res, *mod_args)

        return res, key
