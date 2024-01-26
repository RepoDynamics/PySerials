from typing import Literal as _Literal, Any as _Any
from pathlib import Path as _Path
from enum import Enum as _Enum


class ReadErrorType(_Enum):
    """Enumeration of all possible read error types."""

    FILE_MISSING = "the file does not exist"
    FILE_EMPTY = "the file is empty"
    STRING_EMPTY = "the string is empty"
    DATA_INVALID = "the data is invalid"
    EXTENSION_INVALID = "the file extension is invalid"


class ValidationErrorType(_Enum):
    """Enumeration of all possible validation error types."""

    SCHEMA_INVALID = "the schema is invalid"
    DATA_INVALID = "the data is invalid"


class UpdateErrorType(_Enum):
    """Enumeration of all possible update error types."""

    TYPE_MISMATCH = (
        "type mismatch; the value of '{address}' is of type '{type_source}' in the source data, "
        "but of type '{type_addon}' in the addon data"
    )
    DUPLICATION = (
        "duplication; the value of '{address}' with type {type_source} already exists in the source data"
    )


class PySerialsError(Exception):
    """Base class for all PySerials errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
        return


class ReadError(PySerialsError):
    """Base class for all PySerials read errors."""

    def __init__(
        self,
        error_type: ReadErrorType,
        source_type: _Literal["file", "string"],
        data_type: _Literal["json", "yaml", "toml"] | None = None,
        filepath: _Path | None = None,
        data: str | None = None,
    ):
        self._type = error_type
        self._source_type = source_type
        self._data_type = data_type
        self._filepath = filepath
        self._data = data

        message = f"Failed to read {data_type} data from {source_type}; {error_type.value}."
        super().__init__(message)
        return

    @property
    def type(self) -> ReadErrorType:
        """The type of error."""
        return self._type

    @property
    def source_type(self) -> _Literal["file", "string"]:
        """Source of the data; either 'string' or 'file'."""
        return self._source_type

    @property
    def data_type(self) -> _Literal["json", "yaml", "toml"] | None:
        """The type of data; either 'json', 'yaml', 'toml', or None, in case of an invalid extension error."""
        return self._data_type

    @property
    def filepath(self) -> _Path | None:
        """The path of the input datafile; available only when source-type is file."""
        return self._filepath

    @property
    def data(self) -> str | None:
        """The input data;
        available only when source-type is string, or when the input file was read successfully."""
        return self._data


class ValidationError(PySerialsError):
    """Base class for all PySerials validation errors."""

    def __init__(
        self,
        error_type: ValidationErrorType,
        data: dict | list | str | int | float | bool,
        schema: dict,
        validator: _Any,
    ):
        self._type = error_type
        self._data = data
        self._schema = schema
        self._validator = validator

        message = f"Failed to validate data against schema using validator '{validator}'; {error_type.value}."
        super().__init__(message)
        return


class UpdateError(PySerialsError):
    """Base class for all PySerials update errors."""

    def __init__(self, message: str):
        super().__init__(message)
        return


class DictUpdateError(UpdateError):
    """Base class for all PySerials dict update errors."""

    def __init__(
        self,
        error_type: UpdateErrorType,
        address: str,
        value_data: _Any,
        value_addon: _Any,
    ):
        self._type = error_type
        self._address = address
        self._value_data = value_data
        self._value_addon = value_addon

        error_details = error_type.value.format(
            address=address, type_source=type(value_data), type_addon=type(value_addon)
        )
        message = f"Failed to update dictionary due to {error_details}."
        super().__init__(message)
        return
