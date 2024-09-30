"""Exceptions raised by `pyserials.read` module."""

from __future__ import annotations
from typing import Literal as _Literal
from pathlib import Path as _Path

import ruamel.yaml as _yaml
import json as _json
import mdit as _mdit

from tomlkit.exceptions import TOMLKitError as _TOMLKitError

from pyserials.exception import _base


class PySerialsReadException(_base.PySerialsException):
    """Base class for all exceptions raised by `pyserials.read` module.

    Attributes
    ----------
    source_type : {"file", "string"}
        Type of source from which data was read.
    data_type : {"json", "yaml", "toml"} or None
        Type of input data, if known.
    filepath : pathlib.Path or None
        Path to the input datafile, if data was read from a file.
    """

    def __init__(
        self,
        source_type: _Literal["file", "string"],
        problem,
        section: dict | None = None,
        data_type: _Literal["json", "yaml", "toml"] | None = None,
        filepath: _Path | None = None,
    ):
        intro = _mdit.inline_container(
            "Failed to read",
            f"{data_type.upper()} data" if data_type else "data",
            "from input",
            "string." if source_type == "string" else _mdit.inline_container(
                "file at ", _mdit.element.code_span(filepath), "."
            ),
            separator=" ",
        )
        report = _mdit.document(
            heading="Data Read Error",
            body={
                "intro": intro,
                "problem": problem,
            },
            section=section,
        )
        super().__init__(report)
        self.source_type: _Literal["file", "string"] = source_type
        self.data_type: _Literal["json", "yaml", "toml"] | None = data_type
        self.filepath: _Path | None = filepath
        return


class PySerialsEmptyStringError(PySerialsReadException):
    """Exception raised when a string to be read is empty."""

    def __init__(self, data_type: _Literal["json", "yaml", "toml"]):
        problem = f"The string is empty."
        super().__init__(problem=problem, source_type="string", data_type=data_type)
        return


class PySerialsInvalidFileExtensionError(PySerialsReadException):
    """Exception raised when a file to be read has an unrecognized extension."""

    def __init__(self, filepath: _Path):
        problem = _mdit.inline_container(
            "The file extension must be one of ",
            _mdit.element.code_span('json'),
            ", ",
            _mdit.element.code_span('yaml'),
            ", ",
            _mdit.element.code_span('yml'),
            ", or ",
            _mdit.element.code_span('.toml'),
            ", but got ",
            _mdit.element.code_span(str(filepath.suffix.removeprefix('.'))),
            ". Please provide the extension explicitly, or rename the file to have a valid extension."
        )
        super().__init__(problem=problem, source_type="file", filepath=filepath)
        return


class PySerialsMissingFileError(PySerialsReadException):
    """Exception raised when a file to be read does not exist."""

    def __init__(self, data_type: _Literal["json", "yaml", "toml"], filepath: _Path):
        problem = f"The file does not exist."
        super().__init__(problem=problem, source_type="file", data_type=data_type, filepath=filepath)
        return


class PySerialsEmptyFileError(PySerialsReadException):
    """Exception raised when a file to be read is empty."""

    def __init__(self, data_type: _Literal["json", "yaml", "toml"], filepath: _Path):
        problem = f"The file is empty."
        super().__init__(problem=problem, source_type="file", data_type=data_type, filepath=filepath)
        return


class PySerialsInvalidDataError(PySerialsReadException):
    """Exception raised when the data is invalid.

    Attributes
    ----------
    data : str
        The input data that was supposed to be read.
    """

    def __init__(
        self,
        source_type: _Literal["file", "string"],
        data_type: _Literal["json", "yaml", "toml"],
        data: str,
        cause: Exception,
        filepath: _Path | None = None,
    ):
        self.data = data
        self.cause = cause
        self.problem: str = str(cause)
        self.problem_line: int | None = None
        self.problem_column: int | None = None
        self.problem_data_type: str | None = None
        self.context: str | None = None
        self.context_line: int | None = None
        self.context_column: int | None = None
        self.context_data_type: str | None = None
        self.data_type = data_type

        if isinstance(cause, _yaml.YAMLError):
            self.problem_line = cause.problem_mark.line + 1
            self.problem_column = cause.problem_mark.column + 1
            self.problem_data_type = cause.problem_mark.name.removeprefix("<").removesuffix(">")
            self.problem = cause.problem.strip()
            if cause.context:
                self.context = cause.context.strip()
                self.context_line = cause.context_mark.line + 1
                self.context_column = cause.context_mark.column + 1
                self.context_data_type = cause.context_mark.name.removeprefix("<").removesuffix(">")
        elif isinstance(cause, _json.JSONDecodeError):
            self.problem = cause.msg
            self.problem_line = cause.lineno
            self.problem_column = cause.colno
        elif isinstance(cause, _TOMLKitError):
            self.problem_line = cause.line
            self.problem_column = cause.col
            self.problem = cause.args[0].removesuffix(f" at line {self.problem_line} col {self.problem_column}")
        self.problem = self.problem.strip().capitalize().removesuffix(".")
        description = ["The data is not valid"]
        if self.problem_line:
            description.extend(
                [
                    " at line ",
                    _mdit.element.code_span(str(self.problem_line)),
                    ", column ",
                    _mdit.element.code_span(str(self.problem_column)),
                ]
            )
        description.append(f": {self.problem}.")
        super().__init__(
            problem=description,
            source_type=source_type,
            section=self._report_content(),
            data_type=data_type,
            filepath=filepath
        )
        return

    def _report_content(self) -> dict:

        def make_table(problem, line, column, data_type):
            items = [
                _mdit.element.field_list_item(title=title, body=value) for title, value in [
                    ["Description", problem],
                    ["Line Number", line],
                    ["Column Number", column],
                    ["Data Type", data_type],
                ] if value is not None
            ]
            return _mdit.element.field_list(items)

        content = {
            "problem_details": _mdit.element.admonition(
                title="Problem",
                body=make_table(self.problem, self.problem_line, self.problem_column, self.problem_data_type),
                type="error",
            )
        }
        if self.context:
            content["context_details"] = _mdit.element.admonition(
                title="Context",
                body=make_table(self.context, self.context_line, self.context_column, self.context_data_type),
                type="note",
            )

        code_block_full = _mdit.element.code_block(
            content=self.data,
            language=self.data_type,
            caption="Data",
            line_num=True,
            emphasize_lines=[line for line in (self.problem_line, self.context_line) if line],
            degrade_to_diff=True,
        )
        content["data_full"] = (code_block_full, "full")

        if not (self.problem_line or self.context_line):
            code_block_short = _mdit.element.code_block(
                content=self.data[:1000].strip() + "\n..." if len(self.data) > 1000 else self.data,
                language=self.data_type,
                caption="Data" if len(self.data) <= 1000 else "Data (truncated to first 1000 characters)",
                line_num=True,
            )
        else:
            if self.problem_line and self.context_line:
                line_start = min(self.problem_line, self.context_line)
                line_end = max(self.problem_line, self.context_line)
            else:
                line_start = self.problem_line or self.context_line
                line_end = line_start
            data_lines = self.data.splitlines()
            selected_lines = data_lines[line_start - 1:line_end]
            code_block_short = _mdit.element.code_block(
                content="\n".join(selected_lines),
                language=self.data_type,
                caption="Data",
                line_num=True,
                line_num_start=line_start,
                emphasize_lines=list({1, len(selected_lines)}),
            )
        content["data_short"] = (code_block_short, ("short", "console"))
        container = _mdit.block_container(content)
        doc = _mdit.document(heading="Error Details", body=container)
        return {"details": doc}
