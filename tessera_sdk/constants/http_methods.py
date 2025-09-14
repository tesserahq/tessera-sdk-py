"""
HTTP method constants for the Tessera SDK.
"""


class HTTPMethods:
    """HTTP method constants."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

    # HTTP method list for retry configuration
    ALL_METHODS = [HEAD, GET, OPTIONS, POST, PUT, DELETE]
