import warnings

# Special characters documentation:
# https://docs.influxdata.com/influxdb/v1.4/write_protocols/line_protocol_reference/#special-characters
# Although not in the official docs, new line characters are removed in order to avoid issues.
key_escape = str.maketrans({'\\': '\\\\', ',': r'\,', ' ': r'\ ', '=': r'\=', '\n': ''})
tag_escape = str.maketrans({'\\': '\\\\', ',': r'\,', ' ': r'\ ', '=': r'\=', '\n': ''})
str_escape = str.maketrans({'\\': '\\\\', '"': r'\"', '\n': ''})
measurement_escape = str.maketrans({'\\': '\\\\', ',': r'\,', ' ': r'\ ', '\n': ''})


def escape(string, escape_pattern):
    """Assistant function for string escaping"""
    try:
        return string.translate(escape_pattern)
    except AttributeError:
        warnings.warn("Non-string-like data passed. "
                      "Attempting to convert to 'str'.")
        return str(string).translate(tag_escape)
