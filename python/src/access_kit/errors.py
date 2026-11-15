"""Public, sanitized infrastructure errors for application boundary handlers."""


class StorageUnavailable(Exception):
    """Protection/progress storage failed. Deny work rather than bypass admission."""


class ServiceUnavailable(Exception):
    """A configured external service failed without exposing response content."""
