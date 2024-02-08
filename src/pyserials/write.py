from pathlib import Path as _Path
import json as _json
import ruamel.yaml as _yaml
import tomlkit as _tomlkit


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


def to_yaml_string(
    data: dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq,
    end_of_file_newline: bool = True,
) -> str:
    return _yaml.YAML(typ=["rt", "string"]).dumps(data, add_final_eol=end_of_file_newline)


def to_toml_string(
    data: dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq,
    sort_keys: bool = True,
) -> str:
    return _tomlkit.dumps(data, sort_keys=sort_keys)


def to_json_string(
    data: dict | list | str | int | float | bool | _yaml.CommentedMap | _yaml.CommentedSeq,
    sort_keys: bool = True,
    indent: int | None = None,
) -> str:
    return _json.dumps(data, indent=indent, sort_keys=sort_keys)
