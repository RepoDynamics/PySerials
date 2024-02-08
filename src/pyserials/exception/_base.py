"""PySerials base Exception class."""


class PySerialsException(Exception):
    """Base class for all exceptions raised by PySerials."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
        return
