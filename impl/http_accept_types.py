'''
#  Copyright©2022, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

Implements HTTP Accept Header parsing.

Note this borrows heavily from the python accept-types library,
though we chose to implement here since additional support
is needed for handling optional profiles.
'''

import re
import decimal

# Matches 'text' or 'application'
major_type_str = r'[a-zA-Z0-9._-]+'

# Matches 'html', or 'xml+gml'
minor_type_str = r'[a-zA-Z0-9._+-]+'

# Matches '*', 'image/*', or 'image/png'
valid_mime_type = re.compile(
    r'^(?:\*|{major_type}/\*|{major_type}/{minor_type})$'.format(
        major_type=major_type_str, minor_type=minor_type_str
    )
)

# Matches the 'q=1.23' from the parameters of an Accept mime type
q_match = re.compile(r'(?:^|;)\s*q=([0-9.-]+)(?:$|;)')

MEDIA_HTML = ('text/html', 'application/xhtml+xml',)
MEDIA_JSON = ('application/json', 'text/json',)
MEDIA_JSONLD = ('application/ld+json',)
MEDIA_TEXT = ('text/plain', '*/*',)
MEDIA_XML = ('text/xml', 'application/xml',)
# Inflection requests
MEDIA_INFLECTION = MEDIA_HTML + MEDIA_TEXT + MEDIA_JSON
MEDIA_ALL = MEDIA_HTML + MEDIA_JSON + MEDIA_JSONLD + MEDIA_TEXT + MEDIA_XML

class AcceptableType:
    mime_type = None
    weight = decimal.Decimal(1)
    pattern = None

    def __init__(self, raw_mime_type):
        bits = raw_mime_type.split(';', 1)

        mime_type = bits[0]
        if not valid_mime_type.match(mime_type):
            raise ValueError('"%s" is not a valid mime type' % mime_type)

        tail = ''
        if len(bits) > 1:
            tail = bits[1]

        self.mime_type = mime_type
        self.weight = get_weight(tail)
        self.pattern = get_pattern(mime_type)

    def matches(self, mime_type):
        return self.pattern.match(mime_type)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        display = self.mime_type
        if self.weight != decimal.Decimal(1):
            display += '; q=%0.2f' % self.weight

        return display

    def __repr__(self):
        return '<AcceptableType {0}>'.format(self)

    def __eq__(self, other):
        if not isinstance(other, AcceptableType):
            return NotImplemented
        return (self.mime_type, self.weight) == (other.mime_type, other.weight)

    def __lt__(self, other):
        if not isinstance(other, AcceptableType):
            return NotImplemented
        return self.weight < other.weight


def get_best_match(header, available_types):
    """Find the best mime type to respond to a request with,
    from an ``Accept`` header and list of response mime types
    the application supports.

    .. code-block:: python

        return_data = reticulate_splines()
        return_type = get_best_match(
            request.META.get('HTTP_ACCEPT'),
            ['text/html', 'application/xml', 'text/json'])
        if return_type == 'text/html':
            return render_template('response.html', return_data)
        if return_type == 'application/xml':
            return convert_to_xml(return_data)
        if return_type == 'application/json':
            return json.dumps(return_data)

    :param header: The HTTP ``Accept`` header from the request.
    :type header: str
    :param available_types: The response mime types the application supports.
    :type available_types: List[str]
    :return: The best matching mime type from the supported response
        mime types, or ``None`` if there are no valid matches.
    """
    acceptable_types = parse_header(header)

    for acceptable_type in acceptable_types:
        for available_type in available_types:
            if acceptable_type.matches(available_type):
                return available_type

    return None


def parse_header(header):
    """Parse an ``Accept`` header into a sorted list of :class:`AcceptableType`
    instances.
    """
    raw_mime_types = header.split(',')
    mime_types = []
    for raw_mime_type in raw_mime_types:
        try:
            mime_types.append(AcceptableType(raw_mime_type.strip()))
        except ValueError:
            pass

    return sorted(mime_types, reverse=True)


def get_weight(tail):
    """Given the tail of a mime type header (the bit after the first ``;``),
    find the ``q`` (weight, or quality) parameter.

    If no valid ``q`` parameter is found, default to ``1``, as per the spec.
    """
    match = re.search(q_match, tail)
    if match:
        try:
            return decimal.Decimal(match.group(1))
        except ValueError:
            pass

    # Default weight is 1
    return decimal.Decimal(1)


def get_pattern(mime_type):
    """Convert a mime type string into a regexp pattern that matches that mime
    type. Supports both literal mime types such as ``image/png``, and wildcard
    mime types such as ``image/*``.

    :param mime_type: The mime type string to build a pattern for
    :type mime_type: str
    :return: A regexp that matches the mime_type string.
    """
    # *: Simple match all case
    if mime_type == '*':
        return valid_mime_type
    # image/*: Match the major type
    if mime_type.endswith('*'):
        return re.compile('^' + re.escape(mime_type[:-1]) + minor_type_str + '$')
    # All other cases, match the exact mime type string
    return re.compile('^' + re.escape(mime_type) + '$')
