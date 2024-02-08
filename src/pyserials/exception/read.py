"""Exceptions raised by `pyserials.read` module."""


from typing import Literal as _Literal
from pathlib import Path as _Path

from pyserials.exception._base import PySerialsException as _PySerialsException


class PySerialsReadException(_PySerialsException):
    """Base class for all exceptions raised by `pyserials.read` module."""

    def __init__(self, message: str, source_type: _Literal["file", "string"]):
        super().__init__(message=f"Failed to read data from {source_type}. {message}.")
        return


class PySerialsReadFromFileException(PySerialsReadException):
    """Base class for all exceptions raised when reading data from a file.

    Attributes
    ----------
    filepath : pathlib.Path
        The path of the input datafile.
    """
    def __init__(self, message: str, filepath: _Path):
        super().__init__(message=message, source_type="file")
        self.filepath: _Path = filepath
        return


class PySerialsReadFromStringException(PySerialsReadException):
    """Base class for all exceptions raised when reading data from a string.

    Attributes
    ----------
    data_type : {"json", "yaml", "toml"}
        The type of data.
    """

    def __init__(self, message: str, data_type: _Literal["json", "yaml", "toml"]):
        super().__init__(message=message, source_type="string")
        self.data_type = data_type
        return


class PySerialsInvalidFileExtensionError(PySerialsReadFromFileException):
    """Exception raised when a file to be read has an unrecognized extension."""

    def __init__(self, filepath: _Path):
        message = (
            f"The extension of the file at '{filepath}' is invalid; "
            f"expected one of 'json', 'yaml', or 'toml', but got '{filepath.suffix.removeprefix('.')}'. "
            "Please provide the extension explicitly, or rename the file to have a valid extension."
        )
        super().__init__(message=message, filepath=filepath)
        return


class PySerialsMissingFileError(PySerialsReadFromFileException):
    """Exception raised when a file to be read does not exist."""

    def __init__(self, filepath: _Path):
        message = f"The file at '{filepath}' does not exist."
        super().__init__(message=message, filepath=filepath)
        return


class PySerialsEmptyFileError(PySerialsReadFromFileException):
    """Exception raised when a file to be read is empty."""

    def __init__(self, filepath: _Path):
        message = f"The file at '{filepath}' is empty."
        super().__init__(message=message, filepath=filepath)
        return


class PySerialsInvalidDataFileError(PySerialsReadFromFileException):
    """Exception raised when a file to be read is invalid.

    Attributes
    ----------
    data : str
        The input data that was supposed to be read.
    data_type : {"json", "yaml", "toml"}
        The type of data.
    """

    def __init__(self, filepath: _Path, data_type: _Literal["json", "yaml", "toml"], data: str):
        message = f"The {data_type} file at '{filepath}' is invalid."
        super().__init__(message=message, filepath=filepath)
        self.data = data
        self.data_type = data_type
        return


class PySerialsEmptyStringError(PySerialsReadFromStringException):
    """Exception raised when a string to be read is empty."""

    def __init__(self, data_type: _Literal["json", "yaml", "toml"]):
        message = f"The {data_type} string is empty."
        super().__init__(message=message, data_type=data_type)
        return


class PySerialsInvalidDataStringError(PySerialsReadFromStringException):
    """Exception raised when a string to be read is invalid.

    Attributes
    ----------
    data : str
        The input data that was supposed to be read.
    """

    def __init__(self, data_type: _Literal["json", "yaml", "toml"], data: str):
        message = f"The {data_type} string is invalid."
        super().__init__(message=message, data_type=data_type)
        self.data = data
        return
