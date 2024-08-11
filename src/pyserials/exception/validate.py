"""Exceptions raised by `pyserials.validate` module."""


from typing import Any as _Any

import jsonschema as _jsonschema

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
        registry: _Any = None,
    ):
        message = (
            "Failed to validate data against schema "
            f"using validator '{validator.__class__.__name__}': {message}"
        )
        super().__init__(message=message)
        self.data = data
        self.schema = schema
        self.validator = validator
        self.registry = registry
        return


class PySerialsInvalidJsonSchemaError(PySerialsValidateException):
    """Exception raised when data validation fails due to the schema being invalid."""

    def __init__(
        self,
        data: dict | list | str | int | float | bool,
        schema: dict,
        validator: _Any,
        registry: _Any = None,
    ):
        super().__init__(
            message="The schema is invalid.",
            data=data,
            schema=schema,
            validator=validator,
            registry=registry,
        )
        return


class PySerialsJsonSchemaValidationError(PySerialsValidateException):
    """Exception raised when data validation fails due to the data being invalid against the schema."""

    def __init__(
        self,
        errors: list[_jsonschema.exceptions.ValidationError],
        data: dict | list | str | int | float | bool,
        schema: dict,
        validator: _Any,
        registry: _Any = None,
    ):
        self.errors = errors
        self.details = self._create_details()
        super().__init__(
            message=f"The data is invalid against the schema.\n{self.details}",
            data=data,
            schema=schema,
            validator=validator,
            registry=registry,
        )
        return

    def _create_details(self) -> str:
        return

    @staticmethod
    def html_report(
        errors: list[_jsonschema.exceptions.ValidationError],
        full: bool = False,
    ) -> str:
        for error in errors:
            if error.message.startswith(str(error.instance)):
                problem = error.message.removeprefix(str(error.instance))
                msg = f"The data at '{error.json_path}' {problem}"
            else:
                msg = error.message
            msg = f"{msg.removesuffix(".")}."


