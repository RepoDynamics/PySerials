"""Exceptions raised by `pyserials.update` module."""

from typing import Any as _Any

from pyserials.exception._base import PySerialsException as _PySerialsException


class PySerialsUpdateException(_PySerialsException):
    """Base class for all exceptions raised by `pyserials.update` module."""

    def __init__(self, message: str):
        super().__init__(f"Failed to update data. {message}.")
        return


class PySerialsUpdateDictFromAddonException(PySerialsUpdateException):
    """Base class for all exceptions raised by `pyserials.update.dict_from_addon`.

    Attributes
    ----------
    address : str
        The address of the data that failed to update.
    value_data : Any
        The value of the data in the source dictionary.
    value_addon : Any
        The value of the data in the addon dictionary.
    """

    def __init__(
        self,
        message: str,
        address: str,
        value_data: _Any,
        value_addon: _Any,
    ):
        super().__init__(message=message)
        self.address = address
        self.value_data = value_data
        self.value_addon = value_addon
        return


class PySerialsUpdateTemplatedDataException(PySerialsUpdateException):
    """Base class for all exceptions raised by `pyserials.update.templated_data_from_source`.

    Attributes
    ----------
    templated_data : str
        The templated data that failed to update.
    source_data : dict
        The data that was used to update the template.
    template_start : str
        The start marker of the template.
    template_end : str
        The end marker of the template.
    """

    def __init__(
        self,
        message: str,
        templated_data: str,
        source_data: dict,
        template_start: str,
        template_end: str
    ):
        super().__init__(message=message)
        self.templated_data = templated_data
        self.source_data = source_data
        self.template_start = template_start
        self.template_end = template_end
        return


class PySerialsDictUpdateTypeMismatchError(PySerialsUpdateDictFromAddonException):
    """Exception raised when a dict update fails due to a type mismatch."""

    def __init__(self, address: str, value_data: _Any, value_addon: _Any):
        message = (
            f"There was a type mismatch between the source and addon dictionary values at '{address}'; "
            f"the value is of type '{type(value_data).__name__}' in the source data, "
            f"but of type '{type(value_addon).__name__}' in the addon data"
        )
        super().__init__(message=message, address=address, value_data=value_data, value_addon=value_addon)
        return


class PySerialsDictUpdateDuplicationError(PySerialsUpdateDictFromAddonException):
    """Exception raised when a dict update fails due to a duplication."""

    def __init__(self, address: str, value_data: _Any, value_addon: _Any):
        message = (
            f"There was a duplication in the addon dictionary at '{address}'; "
            f"the value of type '{type(value_addon).__name__}' already exists in the source data"
        )
        super().__init__(message=message, address=address, value_data=value_data, value_addon=value_addon)
        return


class PySerialsTemplateUpdateMissingSourceError(PySerialsUpdateTemplatedDataException):
    """Exception raised when a templated data update fails due to a missing key in source data.

    Attributes
    ----------
    address_full : str
        The full address in the source data where the key/index is missing.
    address_missing : str
        The key/index that is missing in the source data at `address_full`.
    """

    def __init__(
        self,
        address_full: str,
        address_missing: str,
        templated_data: str,
        source_data: dict,
        template_start: str,
        template_end: str
    ):
        message = (
            f"The key/index '{address_missing}' is missing in the source data at '{address_full}'"
        )
        super().__init__(
            message=message,
            templated_data=templated_data,
            source_data=source_data,
            template_start=template_start,
            template_end=template_end
        )
        self.address_full = address_full
        self.address_missing = address_missing
        return
