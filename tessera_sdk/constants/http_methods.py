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

    # Common method list (useful for validation / allowlists)
    ALL_METHODS = [HEAD, GET, OPTIONS, POST, PUT, DELETE]
