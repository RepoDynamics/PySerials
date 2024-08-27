"""Exceptions raised by `pyserials.update` module."""

from __future__ import annotations
from typing import Any as _Any, Literal as _Literal

from markitup.html import elem as _html

from pyserials.exception import _base


class PySerialsUpdateException(_base.PySerialsException):
    """Base class for all exceptions raised by `pyserials.update` module.

    Attributes
    ----------
    path : str
        JSONPath to where the update failed.
    data : dict | list | str | int | float | bool
        Data that failed to update.
    data_full : dict | list | str | int | float | bool
        Full data input.
    """

    def __init__(
        self,
        path: str,
        data: dict | list | str | int | float | bool,
        data_full: dict | list | str | int | float | bool,
        description: str,
        description_html: str | _html.Element | None = None,
    ):
        message_template = "Failed to update data at {path}."
        path_console, path_html = _base.format_code(path)
        super().__init__(
            message=message_template.format(path=path_console),
            message_html=message_template.format(path=path_html),
            description=description,
            description_html=description_html,
            report_heading="PySerials Update Error Report",
        )
        self.path = path
        self.data = data
        self.data_full = data_full
        return


class PySerialsUpdateDictFromAddonError(PySerialsUpdateException):
    """Base class for all exceptions raised by `pyserials.update.dict_from_addon`.

    Attributes
    ----------
    data_addon : Any
        Value of the failed data in the addon dictionary.
    data_addon_full : dictionary
        Full addon input.
    """

    def __init__(
        self,
        problem_type: _Literal["duplicate", "type_mismatch"],
        path: str,
        data: _Any,
        data_full: dict,
        data_addon: _Any,
        data_addon_full: dict,
    ):
        self.type_data = type(data)
        self.type_data_addon = type(data_addon)
        type_data_console, type_data_html = _base.format_code(self.type_data.__name__)
        type_data_addon_console, type_data_addon_html = _base.format_code(self.type_data_addon.__name__)
        path_console, path_html = _base.format_code(path)
        kwargs_console, kwargs_html = (
            {"path": path, "type_data": type_data, "type_data_addon": type_data_addon}
            for path, type_data, type_data_addon in zip(
                (path_console, path_html),
                (type_data_console, type_data_html),
                (type_data_addon_console, type_data_addon_html),
            )
        )
        description_template = (
            "There was a duplicate in the addon dictionary; "
            "the value of type {type_data_addon} already exists in the source data."
        ) if problem_type == "duplicate" else (
            "There was a type mismatch between the source and addon dictionary values; "
            "the value is of type {type_data} in the source data, "
            "but of type {type_data_addon} in the addon data."
        )
        super().__init__(
            description=description_template.format(**kwargs_console),
            description_html=description_template.format(**kwargs_html),
            path=path,
            data=data,
            data_full=data_full,
        )
        self.problem_type: _Literal["duplicate", "type_mismatch"] = problem_type
        self.data_addon = data_addon
        self.data_addon_full = data_addon_full
        return


class PySerialsUpdateTemplatedDataError(PySerialsUpdateException):
    """Exception raised when updating templated data fails.

    Attributes
    ----------
    path_invalid : str
        JSONPath that caused the update to fail.
    data_source : dict
        Source data that was used to update the template.
    template_start : str
        The start marker of the template.
    template_end : str
        The end marker of the template.
    """

    def __init__(
        self,
        description_template: str,
        path_invalid: str,
        path: str,
        data: str,
        data_full: dict | list | str | int | float | bool,
        data_source: dict,
        template_start: str,
        template_end: str,
    ):
        path_invalid_console, path_invalid_html = _base.format_code(path_invalid.replace("'", ""))
        super().__init__(
            description=description_template.format(path_invalid=path_invalid_console),
            description_html=description_template.format(path_invalid=path_invalid_html),
            path=path.replace("'", ""),
            data=data,
            data_full=data_full,
        )
        self.path_invalid = path_invalid
        self.data_source = data_source
        self.template_start = template_start
        self.template_end = template_end
        return
