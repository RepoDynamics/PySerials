"""PySerials base Exception class."""

from __future__ import annotations
from typing import Literal as _Literal
import ansi_sgr as _sgr
from markitup import html as _html, doc as _doc
from exceptionman import ReporterException as _ReporterException


_ANSI_HEADING_STYLE = {
    1: _sgr.style(text_styles="bold", background_color="red"),
    2: _sgr.style(text_styles="bold", background_color="yellow"),
    3: _sgr.style(text_styles="bold", background_color="green"),
    4: _sgr.style(text_styles="bold", background_color="blue"),
    5: _sgr.style(text_styles="bold", background_color="magenta"),
    6: _sgr.style(text_styles="bold", background_color="cyan"),
}


class PySerialsException(_ReporterException):
    """Base class for all exceptions raised by PySerials."""

    def __init__(
        self,
        message: str,
        description: str | None = None,
        message_html: str | _html.Element | None = None,
        description_html: str | _html.Element | None = None,
        report_heading: str = "PySerials Error Report",
    ):
        super().__init__(
            message=message,
            description=description,
            message_html=message_html,
            description_html=description_html,
            report_heading=report_heading,
        )
        return


def ansi_heading(section: list[int], title: str) -> str:
    """Get an ANSI SGR formatted heading."""
    sec = ".".join(str(n) for n in section)
    sec_level = min(len(section), 6)
    heading = f" {sec}. {title} "
    return _sgr.format(heading, control_sequence=_ANSI_HEADING_STYLE[sec_level])


def ansi_bold(text: str) -> str:
    return _sgr.format(text, control_sequence=_sgr.style(text_styles="bold"))


def format_code(code: str) -> tuple[str, str]:
    console = _sgr.format(
        code, control_sequence=_sgr.style(text_color=(220, 220, 220), background_color=(20, 20, 20))
    )
    html = str(_html.elem.code(code))
    return console, html