from typing import Literal as _Literal
from pathlib import Path as _Path
import json as _json
import ruamel.yaml as _yaml
import tomlkit as _tomlkit


def to_string(
    data: dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq,
    data_type: _Literal["json", "yaml", "toml"],
    sort_keys: bool = False,
    indent: int | None = None,
    end_of_file_newline: bool = True,
):
    if data_type == "json":
        return to_json_string(data, sort_keys=sort_keys, indent=indent)
    if data_type == "yaml":
        return to_yaml_string(data, end_of_file_newline=end_of_file_newline)
    return to_toml_string(data, sort_keys=sort_keys)


def to_yaml_string(
    data: dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq,
    end_of_file_newline: bool = True,
) -> str:
    yaml_syntax = _yaml.YAML(typ=["rt", "string"]).dumps(data, add_final_eol=False).removesuffix("\n...")
    return f"{yaml_syntax}\n" if end_of_file_newline else yaml_syntax


def to_toml_string(
    data: dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq,
    sort_keys: bool = False,
) -> str:
    return _tomlkit.dumps(data, sort_keys=sort_keys)


def to_json_string(
    data: dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq,
    sort_keys: bool = False,
    indent: int | None = None,
) -> str:
    return _json.dumps(data, indent=indent, sort_keys=sort_keys)


def to_yaml_file(
    data: dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq,
    path: str | _Path,
    make_dirs: bool = True,
):
    path = _Path(path).resolve()
    if make_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)
    _yaml.YAML().dump(data, path)
    return
