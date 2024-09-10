"""Exceptions raised by `pyserials.update` module."""

from __future__ import annotations
from typing import Any as _Any, Literal as _Literal

import mdit as _mdit

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
        problem,
        section: dict | None = None,
    ):
        intro = _mdit.inline_container(
            "Failed to update data at ",
            _mdit.element.code_span(path),
            "."
        )
        report = _mdit.document(
            heading="Data Update Error",
            body={
                "intro": intro,
                "problem": problem,
            },
            section=section,
        )
        super().__init__(report)
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
        problem = _mdit.inline_container(
            "There was a duplicate in the addon dictionary: ",
            "the value of type",
            _mdit.element.code_span(self.type_data_addon.__name__),
            " already exists in the source data."
        ) if problem_type == "duplicate" else _mdit.inline_container(
            "There was a type mismatch between the source and addon dictionary values: ",
            "the value is of type ",
            _mdit.element.code_span(self.type_data.__name__),
            " in the source data, ",
            "but of type ",
            _mdit.element.code_span(self.type_data_addon.__name__),
            " in the addon data."
        )
        super().__init__(
            path=path,
            data=data,
            data_full=data_full,
            problem=problem,
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
        self.path_invalid = path_invalid.replace("'", "")
        self.data_source = data_source
        self.template_start = template_start
        self.template_end = template_end
        parts = description_template.split("{path_invalid}")
        parts.insert(1, _mdit.element.code_span(self.path_invalid))
        super().__init__(
            path=path.replace("'", ""),
            data=data,
            data_full=data_full,
            problem=_mdit.inline_container(*parts),
        )
        return
