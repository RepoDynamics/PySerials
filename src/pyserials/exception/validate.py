"""Exceptions raised by `pyserials.validate` module."""

from __future__ import annotations
from typing import Any as _Any, Literal as _Literal

import jsonschema as _jsonschema
from markitup.html import elem as _html
from markitup.md import elem as _md
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
        description: str,
        data: dict | list | str | int | float | bool,
        schema: dict,
        validator: _Any,
        registry: _Any = None,
        description_html: str | _html.Element | None = None,
    ):
        validator_name = validator.__class__.__name__
        message_template = "Failed to validate data against schema using validator {validator_name}."
        validator_name_console, validator_name_html = _base.format_code(validator_name)
        super().__init__(
            message=message_template.format(validator_name=validator_name_console),
            message_html=message_template.format(validator_name=validator_name_html),
            description=description,
            description_html=description_html,
            report_heading="PySerials Schema Validation Error Report",
        )
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
            description="The schema is invalid.",
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
        description, description_html = self._parse_errors()
        super().__init__(
            description=description,
            description_html=description_html,
            data=data,
            schema=schema,
            validator=validator,
            registry=registry,
        )
        return

    def _report_content(
        self, mode: _Literal["full", "short"], md: bool
    ) -> list[str | _html.Element] | str | _html.Element | None:
        html_details = []
        for idx, error in enumerate(self.causes):
            section_html = self._report_error(error, section=[idx + 1], mode=mode, md=md)
            html_details.append(section_html)
        return _html.ul([_html.li(detail) for detail in html_details])

    def _parse_errors(self) -> tuple[str, str]:
        count_errors = len(self.causes)
        errors = "an error" if count_errors == 1 else f"{count_errors} errors"
        intro = intro_html = f"Found {errors} in the data at "
        reports = []
        errors_loc = []
        errors_loc_html = []
        for idx, error in enumerate(self.causes):
            error_loc, error_loc_html = _base.format_code(error.json_path)
            errors_loc.append(error_loc)
            errors_loc_html.append(error_loc_html)
            section_console = self._parse_error(error, section=[idx + 1])
            reports.extend(section_console)
        reports_str = "\n".join(reports)
        if len(errors_loc) == 1:
            errors_loc_str = errors_loc[0]
            errors_loc_html_str = errors_loc_html[0]
        elif len(errors_loc) == 2:
            errors_loc_str = " and ".join(errors_loc)
            errors_loc_html_str = " and ".join(errors_loc_html)
        else:
            errors_loc_str = ", ".join(errors_loc[:-1]) + " and " + errors_loc[-1]
            errors_loc_html_str = ", ".join(errors_loc_html[:-1]) + " and " + errors_loc_html[-1]
        intro += f"{errors_loc_str}:\n\n{reports_str}"
        intro_html += f"{errors_loc_html_str}."
        return intro, intro_html

    def _parse_error(
        self,
        error: _jsonschema.exceptions.ValidationError,
        section: list[int]
    ) -> list:
        schema_path = self._create_path(error.absolute_schema_path)
        title, _ = _base.format_code(error.json_path)
        console = [
            _base.ansi_heading(section, title),
            f"- {_base.ansi_bold('Problem')}: {self._parse_error_message(error)}",
            f"- {_base.ansi_bold("Validator Path")}: {schema_path}",
        ]
        if error.context:
            console.append(f"- {_base.ansi_bold("Context")}:")
            for idx, sub_error in enumerate(sorted(error.context, key=lambda x: len(x.context))):
                sub_console = self._parse_error(
                    sub_error,
                    section=section + [idx+1]
                )
                console.extend(self._indent(sub_console, 2))
        return console

    def _report_error(
        self,
        error: _jsonschema.exceptions.ValidationError,
        section: list[int],
        mode: _Literal["full", "short"],
        md: bool
    ) -> _html.Details:
        details = [
            _html.p(f"{_html.b("Problem")}: {self._parse_error_message(error)}"),
            self._create_validator_details(error, mode=mode, md=md),
            self._create_schema_details(error, mode=mode, md=md),
            self._create_instance_details(error, mode=mode, md=md),
        ]
        if error.context:
            contexts = []
            for idx, sub_error in enumerate(sorted(error.context, key=lambda x: len(x.context))):
                sub_html = self._report_error(
                    sub_error,
                    section=section + [idx+1],
                    mode=mode,
                    md=md,
                )
                contexts.append(sub_html)
            context_list = _html.ul([_html.li(context) for context in contexts])
            details.append(f"{_html.b("Context")}: {context_list}")
        _, title = _base.format_code(error.json_path)
        html = _html.details(
            [_html.summary(title), _html.ul([_html.li(elem) for elem in details])]
        )
        return html

    def _create_validator_details(self, error: _jsonschema.exceptions.ValidationError, mode: _Literal["full", "short"], md: bool) -> _html.Details:
        summary = self._create_details_summary("Validator", str(error.validator))
        return summary if mode == "short" else self._make_details(
            content=error.validator_value,
            summary=summary,
            md=md,
        )

    def _create_schema_details(self, error: _jsonschema.exceptions.ValidationError, mode: _Literal["full", "short"], md: bool) -> _html.Details:
        summary = self._create_details_summary("Schema", self._create_path(error.absolute_schema_path))
        return summary if mode == "short" else self._make_details(
            content=error.schema,
            summary=summary,
            md=md,
        )

    def _create_instance_details(self, error: _jsonschema.exceptions.ValidationError, mode: _Literal["full", "short"], md: bool) -> _html.Details:
        summary = self._create_details_summary("Instance", self._create_path(error.absolute_path))
        return summary if mode == "short" else self._make_details(
            content=error.instance,
            summary=summary,
            md=md,
        )

    @staticmethod
    def _make_details(content: dict, summary: str, md: bool) -> _html.Details:
        yaml = _write.to_yaml_string(content, end_of_file_newline=False)
        details_summary = _html.summary(summary)
        details_content = _html.pre(
            _html.code(yaml, {"class": "language-yaml"})
        ) if not md else _md.code_fence(yaml, info="yaml")
        return _html.details([details_summary, details_content])

    def _create_title(self, error: _jsonschema.exceptions.ValidationError) -> tuple[str, str]:
        problem = self._parse_error_message(error)
        title_shell = f"'{error.json_path}': {problem}"
        title_html = f"{_html.code(error.json_path)}: {problem}"
        return title_shell, title_html

    @staticmethod
    def _parse_error_message(error: _jsonschema.exceptions.ValidationError) -> str:
        instance_str = str(error.instance)
        if error.message.startswith(instance_str):
            msg = error.message.removeprefix(str(error.instance)).strip()
            problem = f"Data {msg}"
        else:
            problem = error.message
        return problem

    @staticmethod
    def _indent(text: list, indent: int = 2) -> list:
        return [f"{' ' * indent}{line}" for line in text]

    @staticmethod
    def _create_path(path):
        return "$." + ".".join(str(path_component) for path_component in path)

    @staticmethod
    def _create_details_summary(title: str, code: str) -> str:
        return f"{_html.b(title)}: {_html.code(code)}"