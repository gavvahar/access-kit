"""Sanitized errors: messages never include submitted URLs or response bodies."""


class FetchError(Exception):
    """An upstream request could not be completed safely."""


class BlockedDestination(FetchError):
    """A URL or resolved address is not permitted."""


class TooLarge(FetchError):
    """The announced or streamed body exceeds its byte limit."""


class BadContentType(FetchError):
    """The upstream media type or content encoding is not permitted."""


class TooManyRedirects(FetchError):
    """The redirect limit was exceeded."""


class FetchTimeout(FetchError):
    """The connection or total operation deadline expired."""
