"""Exceptions raised by `pyserials.read` module."""

from __future__ import annotations
from typing import Literal as _Literal
from pathlib import Path as _Path

import ruamel.yaml as _yaml
import json as _json

from markitup import html as _html, md as _md
from tomlkit.exceptions import TOMLKitError as _TOMLKitError

from pyserials.exception._base import PySerialsException as _PySerialsException


class PySerialsReadException(_PySerialsException):
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
        description: str,
        description_html: str | _html.Element | None = None,
        data_type: _Literal["json", "yaml", "toml"] | None = None,
        filepath: _Path | None = None,
    ):
        if source_type == "string":
            source = source_html = "string"
        else:
            source = f"file at '{filepath}'"
            source_html = f"file at <code>{filepath}</code>"
        data_ = f"{data_type.upper()} data" if data_type else "data"
        message_template = f"Failed to read {data_} from input {{source}}."
        super().__init__(
            message=message_template.format(source=source),
            message_html=message_template.format(source=source_html),
            description=description,
            description_html=description_html,
            report_heading="PySerials Read Error Report",
        )
        self.source_type: _Literal["file", "string"] = source_type
        self.data_type: _Literal["json", "yaml", "toml"] | None = data_type
        self.filepath: _Path | None = filepath
        return


class PySerialsEmptyStringError(PySerialsReadException):
    """Exception raised when a string to be read is empty."""

    def __init__(self, data_type: _Literal["json", "yaml", "toml"]):
        description = f"The string is empty."
        super().__init__(description=description, source_type="string", data_type=data_type)
        return


class PySerialsInvalidFileExtensionError(PySerialsReadException):
    """Exception raised when a file to be read has an unrecognized extension."""

    def __init__(self, filepath: _Path):
        description = (
            f"The file extension must be one of 'json', 'yaml', 'yml', or '.toml', "
            f"but got '{filepath.suffix.removeprefix('.')}'. "
            "Please provide the extension explicitly, or rename the file to have a valid extension."
        )
        super().__init__(description=description, source_type="file", filepath=filepath)
        return


class PySerialsMissingFileError(PySerialsReadException):
    """Exception raised when a file to be read does not exist."""

    def __init__(self, data_type: _Literal["json", "yaml", "toml"], filepath: _Path):
        description = f"The file does not exist."
        super().__init__(description=description, source_type="file", data_type=data_type, filepath=filepath)
        return


class PySerialsEmptyFileError(PySerialsReadException):
    """Exception raised when a file to be read is empty."""

    def __init__(self, data_type: _Literal["json", "yaml", "toml"], filepath: _Path):
        description = f"The file is empty."
        super().__init__(description=description, source_type="file", data_type=data_type, filepath=filepath)
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

        if isinstance(cause, _yaml.YAMLError):
            self.problem_line = cause.problem_mark.line + 1
            self.problem_column = cause.problem_mark.column + 1
            self.problem_data_type = cause.problem_mark.name
            self.problem = cause.problem.strip()
            if cause.context:
                self.context = cause.context.strip()
                self.context_line = cause.context_mark.line + 1
                self.context_column = cause.context_mark.column + 1
                self.context_data_type = cause.context_mark.name
        elif isinstance(cause, _json.JSONDecodeError):
            self.problem = cause.msg
            self.problem_line = cause.lineno
            self.problem_column = cause.colno
        elif isinstance(cause, _TOMLKitError):
            self.problem_line = cause.line
            self.problem_column = cause.col
            self.problem = cause.args[0].removesuffix(f" at line {self.problem_line} col {self.problem_column}")
        self.problem = self.problem.strip().capitalize().removesuffix(".")
        description = "The data is not valid"
        if self.problem_line:
            description += f" at line {self.problem_line}, column {self.problem_column}"
        description += f": {self.problem}."
        super().__init__(description=description, source_type=source_type, data_type=data_type, filepath=filepath)
        return

    def _report_content(self, mode: _Literal["full", "short"], md: bool) -> _html.elem.Ul:

        def make_tabel(problem, line, column, data_type):
            rows = [
                [title, value] for title, value in [
                    ["Description", problem],
                    ["Line Number", line],
                    ["Column Number", column],
                    ["Data Type", data_type],
                ] if value is not None
            ]
            return _html.elem.table_from_rows(rows_body=rows)

        content_list = [
            _html.elem.details(
                [
                    _html.elem.summary("❌ Problem"),
                    make_tabel(self.problem, self.problem_line, self.problem_column, self.problem_data_type)
                ]
            ),
        ]
        if self.context:
            content_list.append(
                _html.elem.details(
                    [
                        _html.elem.summary("🔍 Context"),
                        make_tabel(self.context, self.context_line, self.context_column, self.context_data_type)
                    ]
                ),
            )
        data_lines = self.data.splitlines()
        if self.problem_line:
            line_idx = self.problem_line - 1
            problem_line = data_lines[line_idx]
            if md:
                problem_line = f"- {problem_line}"
            else:
                if self.problem_column:
                    col_idx = self.problem_column - 1
                    prob_col = problem_line[col_idx]
                    prob_col_highlight = _html.elem.span(prob_col, {"class": "highlight-char"})
                    problem_line = f"{problem_line[:col_idx]}{prob_col_highlight}{problem_line[col_idx+1:]}"
                problem_line = str(_html.elem.span(problem_line, {"class": "highlight-line"}))
            data_lines[line_idx] = problem_line
        if mode == "short":
            if self.problem_line is not None:
                problem_line_idx = self.problem_line - 1
                start_line = max(0, problem_line_idx)
                end_line = min(len(data_lines), problem_line_idx + 1)
                if self.context_line is not None:
                    context_line_idx = self.context_line - 1
                    start_line = max(0, context_line_idx, problem_line_idx)
                    end_line = min(len(data_lines), context_line_idx + 1, problem_line_idx + 1)
                data_lines = data_lines[start_line:end_line]
        data = "\n".join(data_lines)
        if md:
            code_block = _md.elem.code_fence(data, info="diff")
        else:
            code_block = _html.elem.pre(_html.elem.code(data, {"class": f"language-{self.data_type}"}))
        content_list.append(_html.elem.details([_html.elem.summary("📄 Data"), code_block]))
        return _html.elem.ul([_html.elem.li(content) for content in content_list])
