"""Exceptions raised by `pyserials.validate` module."""

from __future__ import annotations
from typing import Any as _Any

import jsonschema as _jsonschema
import mdit as _mdit
from protocolman import Stringable

from pyserials import write as _write
from pyserials.exception import _base


class PySerialsValidateException(_base.PySerialsException):
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
        problem,
        data: dict | list | str | int | float | bool,
        schema: dict,
        validator: _Any,
        registry: _Any = None,
        section: dict | None = None,
    ):
        intro = _mdit.inline_container(
            "Failed to validate data against schema using validator ",
            _mdit.element.code_span(validator.__class__.__name__),
            "."
        )
        report = _mdit.document(
            heading="Schema Validation Error",
            body={
                "intro": intro,
                "problem": problem,
            },
            section=section,
        )
        super().__init__(report)
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
            problem="The schema is invalid.",
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
        causes: list[_jsonschema.exceptions.ValidationError],
        data: dict | list | str | int | float | bool,
        schema: dict,
        validator: _Any,
        registry: _Any = None,
    ):
        self.causes = causes
        super().__init__(
            problem=self._generate_problem_statement(),
            section={str(idx): self._generate_error_report(error) for idx, error in enumerate(self.causes)},
            data=data,
            schema=schema,
            validator=validator,
            registry=registry,
        )
        return

    def _generate_problem_statement(self):
        error_paths = [_mdit.element.code_span(error.json_path) for error in self.causes]
        error_paths_str = self._join_list(error_paths)
        count_errors = len(error_paths)
        problem = _mdit.inline_container(
            "Found ",
            "an error " if count_errors == 1 else f"{count_errors} errors ",
            "in the data at ",
            error_paths_str,
            "."
        )
        return problem

    def _generate_error_report(
        self,
        error: _jsonschema.exceptions.ValidationError,
    ) -> _mdit.Document:
        problem = self._parse_error_message(error)
        short_ver_fieldlist_items = [
            _mdit.element.field_list_item("Problem", problem),
            _mdit.element.field_list_item(
                "Validator Path", _mdit.element.code_span(self._create_path(error.absolute_schema_path))
            ),
        ]
        full_ver_items = [
            _mdit.inline_container(problem),
            self._make_yaml_code_admo(
                admo_type="error",
                title="Validator",
                title_details=str(error.validator),
                content=error.validator_value,
            ),
            self._make_yaml_code_admo(
                admo_type="error",
                title="Schema",
                title_details=self._create_path(error.absolute_schema_path),
                content=error.schema,
            ),
            self._make_yaml_code_admo(
                admo_type="error",
                title="Instance",
                title_details=self._create_path(error.absolute_path),
                content=error.instance,
            ),
        ]
        section = {}
        if error.context:
            context_paths = []
            for idx, sub_error in enumerate(sorted(error.context, key=lambda x: len(x.context))):
                section[str(idx)] = self._generate_error_report(sub_error)
                context_paths.append(_mdit.element.code_span(sub_error.json_path))
            context_paths_joined = self._join_list(context_paths)
            short_ver_fieldlist_items.insert(
                1,
                _mdit.element.field_list_item(
                    f"Context Path{'s' if len(context_paths) > 1 else ''}",
                    context_paths_joined
                )
            )
            err = "an error" if len(context_paths) == 1 else f"{len(context_paths)} errors"
            full_ver_items[0].append(
                f" This was caused by {err} at {context_paths_joined}.",
            )
        doc = _mdit.document(
            heading=_mdit.element.code_span(error.json_path),
            body={
                "short": (_mdit.element.field_list(short_ver_fieldlist_items), ("short", "console")),
                "full": (_mdit.block_container(*full_ver_items), "full"),
            },
            section=section,
        )
        return doc

    @staticmethod
    def _make_yaml_code_admo(admo_type: str, title: str, title_details: str, content: dict) -> _mdit.element.Admonition:
        code_block = _mdit.element.code_block(
            content=_write.to_yaml_string(content, end_of_file_newline=False),
            language="yaml",
        )
        admo = _mdit.element.admonition(
            title=_mdit.inline_container(f"**{title}**: ", _mdit.element.code_span(title_details)),
            body=code_block,
            type=admo_type,
            dropdown=True,
        )
        return admo

    @staticmethod
    def _parse_error_message(error: _jsonschema.exceptions.ValidationError) -> str:
        instance_str = str(error.instance)
        if error.message.startswith(instance_str):
            msg = error.message.removeprefix(str(error.instance)).strip()
            problem = f"Data {msg}"
        else:
            problem = error.message
        return f"{problem.removeprefix(".")}."

    @staticmethod
    def _create_path(path):
        return "$." + ".".join(str(path_component) for path_component in path)

    @staticmethod
    def _join_list(
        items: list,
        sep: Stringable = ", ",
        sep_last: Stringable = ", and ",
        sep_pair: Stringable = " and ",
    ) -> Stringable:
        if len(items) == 1:
            return items[0]
        elif len(items) == 2:
            return _mdit.inline_container(items[0], sep_pair, items[1])
        container = []
        for item in items[:-1]:
            container.extend([item, sep])
        container.pop()
        container.extend([sep_last, items[-1]])
        return _mdit.inline_container(*container)