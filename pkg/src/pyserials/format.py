import tomlkit as _tomlkit
import ruamel.yaml as _yaml
import ruamel.yaml.comments as _yaml_comments
from typing import Literal as _Literal


def to_toml_object(
    data: str | list | dict,
    toml_type: _Literal[
        "str", "table", "array", "inline_table", "array_of_inline_tables", "table_of_arrays", "table_of_tables"
    ],
):
    match toml_type:
        case "str":
            return data
        case "table":
            return data
        case "array":
            array = _tomlkit.array().multiline(True)
            array.extend(data)
            return array
        case "inline_table":
            inline = _tomlkit.inline_table()
            inline.update(data)
            return inline
        case "array_of_inline_tables":
            arr = _tomlkit.array().multiline(True)
            for table in data:
                tab = _tomlkit.inline_table()
                tab.update(table)
                arr.append(tab)
            return arr
        case "table_of_arrays":
            return {tab_key: _tomlkit.array(arr).multiline(True) for tab_key, arr in data.items()}
        case "table_of_tables":
            return _tomlkit.table(is_super_table=True).update(data)
        case _:
            raise ValueError(f"Unknown data type {toml_type}.")


def to_yaml_array(
    data: list,
    inline: bool = True,
) -> _yaml_comments.CommentedSeq:
    """Convert a list to a YAML array.

    Parameters
    ----------
    data : list
        The list to convert.
    inline : bool
        Whether to use inline (i.e., flow) or block style.
    """
    array = _yaml_comments.CommentedSeq()
    array.fa.set_flow_style() if inline else array.fa.set_block_style()
    array.extend(data)
    return array
