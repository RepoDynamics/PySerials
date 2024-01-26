from typing import Literal as _Literal
import json as _json
from pathlib import Path as _Path
from functools import partial as _partial
import tomlkit as _tomlkit
from tomlkit.exceptions import TOMLKitError as _TOMLKitError
import ruamel.yaml as _yaml

import pyserials.exception as _exception


def from_file(
    path: str | _Path,
    data_type: _Literal["json", "yaml", "toml"] | None = None,
    json_strict: bool = True,
    yaml_safe: bool = True,
    toml_as_dict: bool = False,
):
    if data_type is None:
        data_type = _Path(path).suffix.removeprefix(".")
        if data_type == "yml":
            data_type = "yaml"
        if data_type not in ("json", "yaml", "toml"):
            raise _exception.ReadError(
                error_type=_exception.ReadErrorType.EXTENSION_INVALID,
                source_type="file",
                filepath=path,
            )
    if data_type == "json":
        return json_from_file(path=path, strict=json_strict)
    if data_type == "yaml":
        return yaml_from_file(path=path, safe=yaml_safe)
    return toml_from_file(path=path, as_dict=toml_as_dict)


def from_string(
    data: str,
    data_type: _Literal["json", "yaml", "toml"],
    json_strict: bool = True,
    yaml_safe: bool = True,
    toml_as_dict: bool = False,
):
    if data_type == "json":
        return json_from_string(data=data, strict=json_strict)
    if data_type == "yaml":
        return yaml_from_string(data=data, safe=yaml_safe)
    return toml_from_string(data=data, as_dict=toml_as_dict)


def toml(
    source: str | _Path, as_dict: bool = False
) -> _tomlkit.TOMLDocument | dict:
    if isinstance(source, str):
        return toml_from_string(data=source, as_dict=as_dict)
    return toml_from_file(path=source, as_dict=as_dict)


def toml_from_string(data: str, as_dict: bool = False) -> _tomlkit.TOMLDocument | dict:
    content = _read_from_string(data=data, data_type="toml", loader=_tomlkit.loads, exception=_TOMLKitError)
    if as_dict:
        return dict(content)
    return content


def toml_from_file(path: str | _Path, as_dict: bool = False) -> _tomlkit.TOMLDocument | dict:
    content = _read_from_file(
        path=path,
        data_type="toml",
        loader=_tomlkit.loads,
        exception=_TOMLKitError
    )
    if as_dict:
        return dict(content)
    return content


def json(source: str | _Path, strict: bool = True) -> dict | list | str | int | float | bool:
    if isinstance(source, str):
        return json_from_string(data=source, strict=strict)
    return json_from_file(path=source, strict=strict)


def json_from_string(data: str, strict: bool = True) -> dict | list | str | int | float | bool:
    content = _read_from_string(
        data=data,
        data_type="json",
        loader=_partial(_json.loads, strict=strict),
        exception=_json.JSONDecodeError
    )
    return content


def json_from_file(path: str | _Path, strict: bool = True) -> dict | list | str | int | float | bool:
    content = _read_from_file(
        path=path,
        data_type="json",
        loader=_partial(_json.loads, strict=strict),
        exception=_json.JSONDecodeError
    )
    return content


def yaml(
    source: str | _Path, safe: bool = True
) -> dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq:
    if isinstance(source, str):
        return yaml_from_string(data=source, safe=safe)
    return yaml_from_file(path=source, safe=safe)


def yaml_from_string(
    data: str, safe: bool = True
) -> dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq:
    content = _read_from_string(
        data=data,
        data_type="yaml",
        loader=_yaml.YAML(typ="safe" if safe else "rt").load,
        exception=_yaml.YAMLError
    )
    return content


def yaml_from_file(
    path: str | _Path, safe: bool = True
) -> dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq:
    content = _read_from_file(
        path=path,
        data_type="yaml",
        loader=_yaml.YAML(typ="safe" if safe else "rt").load,
        exception=_yaml.YAMLError
    )
    return content


def _read_from_file(
    path: str | _Path,
    data_type: _Literal["json", "yaml", "toml"],
    loader,
    exception,
):
    path = _Path(path).resolve()
    common_error_args = {"source_type": "file", "data_type": data_type, "filepath": path}
    if not path.is_file():
        raise _exception.ReadError(error_type=_exception.ReadErrorType.FILE_MISSING, **common_error_args)
    data = path.read_text()
    common_error_args["data"] = data
    if data.strip() == "":
        raise _exception.ReadError(error_type=_exception.ReadErrorType.FILE_EMPTY, **common_error_args)
    try:
        content = loader(data)
    except exception as e:
        raise _exception.ReadError(
            error_type=_exception.ReadErrorType.DATA_INVALID, **common_error_args
        ) from e
    return content


def _read_from_string(
    data: str,
    data_type: _Literal["json", "yaml", "toml"],
    loader,
    exception,
):
    common_error_args = {"source_type": "string", "data": data, "data_type": data_type}
    if not data.strip():
        raise _exception.ReadError(error_type=_exception.ReadErrorType.STRING_EMPTY, **common_error_args)
    try:
        content = loader(data)
    except exception as e:
        raise _exception.ReadError(
            error_type=_exception.ReadErrorType.DATA_INVALID, **common_error_args
        ) from e
    return content
