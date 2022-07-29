import re
import string


class PartialFormatter(string.Formatter):
    """
    Used for formatting NamerConfig.inplace_name and NamerConfig.
    """

    supported_keys = [
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
    ]

    def __init__(self, missing="~~", bad_fmt="!!"):
        self.missing, self.bad_fmt = missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val = super().get_field(field_name, args, kwargs)
        except (KeyError, AttributeError) as err:
            val = None, field_name
            if field_name not in self.supported_keys:
                raise KeyError(f"Key {field_name} not in support keys: {self.supported_keys}") from err
        return val

    def format_field(self, value, format_spec: str):
        if value is None:
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
            if self.bad_fmt is not None:
                return self.bad_fmt
            raise
