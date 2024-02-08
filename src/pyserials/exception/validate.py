"""Exceptions raised by `pyserials.validate` module."""


from typing import Any as _Any

from pyserials.exception._base import PySerialsException as _PySerialsException


class PySerialsValidateException(_PySerialsException):
    """Base class for all exceptions raised by `pyserials.validate` module.

    Attributes
    ----------
    data : dict | list | str | int | float | bool
        The data that failed validation.
    schema : dict
        The schema that the data failed to validate against.
    validator : Any
        The validator that was used to validate the data against the schema.
    """

    def __init__(
        self,
        message: str,
        data: dict | list | str | int | float | bool,
        schema: dict,
        validator: _Any,
    ):
        message = (
            "Failed to validate data against schema "
            f"using validator '{validator.__class__.__name__}'; {message}."
        )
        super().__init__(message=message)
        self.data = data
        self.schema = schema
        self.validator = validator
        return


class PySerialsSchemaValidationError(PySerialsValidateException):
    """Exception raised when data validation fails due to the data being invalid against the schema."""

    def __init__(
        self,
        data: dict | list | str | int | float | bool,
        schema: dict,
        validator: _Any,
    ):
        super().__init__(
            message="the data is invalid",
            data=data,
            schema=schema,
            validator=validator,
        )
        return


class PySerialsInvalidSchemaError(PySerialsValidateException):
    """Exception raised when data validation fails due to the schema being invalid."""

    def __init__(
        self,
        data: dict | list | str | int | float | bool,
        schema: dict,
        validator: _Any,
    ):
        super().__init__(
            message="the schema is invalid",
            data=data,
            schema=schema,
            validator=validator,
        )
        return
