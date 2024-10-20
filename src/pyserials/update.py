from __future__ import annotations as _annotations
from typing import TYPE_CHECKING as _TYPE_CHECKING
import re as _re

import jsonpath_ng as _jsonpath
from jsonpath_ng import exceptions as _jsonpath_exceptions

import pyserials.exception as _exception

if _TYPE_CHECKING:
    from typing import Literal, Callable, Sequence


def dict_from_addon(
    data: dict,
    addon: dict,
    append_list: bool = True,
    append_dict: bool = True,
    raise_duplicates: bool = False,
    raise_type_mismatch: bool = True,
) -> dict[str, list[str]]:
    """Recursively update a dictionary from another dictionary."""
    def recursive(source: dict, add: dict, path: str, log: dict):

        def raise_error(typ: Literal["duplicate", "type_mismatch"]):
            raise _exception.update.PySerialsUpdateDictFromAddonError(
                problem_type=typ,
                path=fullpath,
                data=source[key],
                data_full=data,
                data_addon=value,
                data_addon_full=addon,
            )

        for key, value in add.items():
            fullpath = f"{path}.{key}"
            if key not in source:
                log["added"].append(fullpath)
                source[key] = value
                continue
            if type(source[key]) is not type(value):
                if raise_type_mismatch:
                    raise_error(typ="type_mismatch")
                continue
            if not isinstance(value, (list, dict)):
                if raise_duplicates:
                    raise_error(typ="duplicate")
                log["skipped"].append(fullpath)
            elif isinstance(value, list):
                if append_list:
                    appended = False
                    for elem in value:
                        if elem not in source[key]:
                            source[key].append(elem)
                            appended = True
                    if appended:
                        log["list_appended"].append(fullpath)
                elif raise_duplicates:
                    raise_error(typ="duplicate")
                else:
                    log["skipped"].append(fullpath)
            else:
                if append_dict:
                    recursive(source=source[key], add=value, path=f"{fullpath}.", log=log)
                elif raise_duplicates:
                    raise_error(typ="duplicate")
                else:
                    log["skipped"].append(fullpath)
        return log
    full_log = recursive(
        source=data, add=addon, path="$", log={"added": [], "skipped": [], "list_appended": []}
    )
    return full_log


def data_from_jsonschema(data: dict | list, schema: dict) -> None:
    """Fill missing data in a data structure with default values from a JSON schema."""
    if 'properties' in schema:
        for prop, subschema in schema['properties'].items():
            if 'default' in subschema:
                data.setdefault(prop, subschema['default'])
            if prop in data:
                data_from_jsonschema(data[prop], subschema)
    elif 'items' in schema and isinstance(data, list):
        for item in data:
            data_from_jsonschema(item, schema['items'])
    return


def remove_keys(data: dict | list, keys: str | Sequence[str]):
    def recursive_pop(d):
        if isinstance(d, dict):
            return {k: recursive_pop(v) for k, v in d.items() if k not in keys}
        if isinstance(d, list):
            return [recursive_pop(v) for v in d]
        return d
    if isinstance(keys, str):
        keys = [keys]
    return recursive_pop(data)


class TemplateFiller:

    def __init__(
        self,
        marker_start: str = "${{",
        marker_end: str = "}}",
        marker_unpack_start: str = "*{{",
        marker_unpack_end: str = "}}",
        implicit_root: bool = True,
        stringer: Callable[[str], str] = str,
    ):
        def make_regex(start, end):
            start_esc = _re.escape(start)
            end_esc = _re.escape(end)
            regex_sub = rf"{start_esc}([^{end_esc}]+){end_esc}"
            return _re.compile(regex_sub)

        self._marker_start = marker_start
        self._marker_end = marker_end
        self._pattern_template = make_regex(marker_start, marker_end)
        self._pattern_template_unpack = make_regex(marker_unpack_start, marker_unpack_end)
        self._add_prefix = implicit_root
        self._stringer = stringer
        self._data = None
        self._source = None
        self._recursive = None
        self._path = None
        self._raise_no_match = None
        self._template_keys = None
        self._ignore_templates = True
        return

    def fill(
        self,
        templated_data: dict | list | str,
        source_data: dict | list,
        current_path: str = "",
        always_list: bool = True,
        recursive: bool = True,
        raise_no_match: bool = True,
        relative_template_keys: list[str] | None = None,
    ):
        self._data = templated_data
        self._source = source_data
        self._recursive = recursive
        self._raise_no_match = raise_no_match
        self._template_keys = relative_template_keys or []
        path = (f"$.{current_path}" if self._add_prefix else current_path) if current_path else "$"
        if not relative_template_keys:
            self._ignore_templates = False
            return self._recursive_subst(
                templ=self._data,
                current_path=path,
                always_list=always_list,
                relative_path_anchor=path,
            )
        self._ignore_templates = True
        first_pass = self._recursive_subst(
            templ=self._data,
            current_path=path,
            always_list=always_list,
            relative_path_anchor=path,
        )
        if self._data is self._source:
            self._source = first_pass
        self._data = first_pass
        self._ignore_templates = False
        return self._recursive_subst(
            templ=self._data,
            current_path=path,
            always_list=always_list,
            relative_path_anchor=path,
        )

    def _recursive_subst(self, templ, current_path: str, always_list: bool, relative_path_anchor: str):

        def raise_error(
            path_invalid: str,
            description_template: str,
        ):
            raise _exception.update.PySerialsUpdateTemplatedDataError(
                description_template=description_template,
                path_invalid=path_invalid,
                path=current_path,
                data=templ,
                data_full=self._data,
                data_source=self._source,
                template_start=self._marker_start,
                template_end=self._marker_end,
            )

        def _rec_match(expr):

            def raise_error_path_invalid():
                raise_error(
                    path_invalid=str(expr),
                    description_template="Path {path_invalid} is missing in the source data.",
                )

            matches = expr.find(self._source)
            if matches:
                return matches
            if isinstance(expr.left, _jsonpath.Root):
                raise_error_path_invalid()
            whole_matches = []
            left_matches = _rec_match(expr.left)
            for left_match in left_matches:
                left_match_filled = self._recursive_subst(
                    left_match.value, current_path=str(expr.left), always_list=False, relative_path_anchor=str(expr.left)
                ) if isinstance(left_match.value, str) else left_match.value
                right_matches = expr.right.find(left_match_filled)
                whole_matches.extend(right_matches)
            if not whole_matches:
                raise_error_path_invalid()
            return whole_matches

        def get_address_value(re_match):
            path, num_periods = self._remove_leading_periods(re_match.group(1).strip())
            if num_periods == 0:
                path = f"$.{path}" if self._add_prefix else path
            try:
                path_expr = _jsonpath.parse(path)
            except _jsonpath_exceptions.JSONPathError:
                raise_error(
                    path_invalid=path,
                    description_template="JSONPath expression {path_invalid} is invalid.",
                )
            if self._ignore_templates:
                path_fields = self._extract_fields(path_expr)
                has_template_key = any(field in self._template_keys for field in path_fields)
                if has_template_key:
                    return re_match.string
            if num_periods:
                root_path_expr = _jsonpath.parse(relative_path_anchor)
                for period in range(num_periods):
                    if isinstance(root_path_expr, _jsonpath.Root):
                        raise_error(
                            path_invalid=path,
                            description_template=(
                                "Relative path {path_invalid} is invalid; "
                                f"reached root but still {num_periods - period} levels remaining."
                            ),
                        )
                    root_path_expr = root_path_expr.left
                path_expr = root_path_expr.child(path_expr)
            return get_value(path_expr)

        def get_value(jsonpath):
            matches = _rec_match(jsonpath)
            values = [m.value for m in matches]
            if not values and self._raise_no_match:
                raise_error(
                    path_invalid=str(jsonpath),
                    description_template="JSONPath expression {path_invalid} did not match any data.",
                )
            single = len(values) == 1 and not always_list
            output = values[0] if single else values
            if not self._recursive:
                return output
            if relative_path_anchor == current_path:
                path_fields = self._extract_fields(jsonpath)
                has_template_key = any(field in self._template_keys for field in path_fields)
                _rel_path_anchor = current_path if has_template_key else str(jsonpath)
            else:
                _rel_path_anchor = relative_path_anchor
            return self._recursive_subst(
                output,
                current_path=str(jsonpath),
                always_list=always_list,
                relative_path_anchor=_rel_path_anchor
            )

        def get_relative_path(new_path):
            return new_path if current_path == relative_path_anchor else relative_path_anchor

        if isinstance(templ, str):
            match_whole_str = self._pattern_template.fullmatch(templ) or self._pattern_template_unpack.fullmatch(templ)
            if match_whole_str:
                return get_address_value(match_whole_str)
            return self._pattern_template.sub(
                lambda x: self._stringer(get_address_value(x)),
                templ
            )
        if isinstance(templ, list):
            out = []
            for idx, elem in enumerate(templ):
                new_path = f"{current_path}[{idx}]"
                elem_filled = self._recursive_subst(
                    templ=elem, current_path=new_path, always_list=always_list, relative_path_anchor=get_relative_path(new_path),
                )
                if isinstance(elem, str) and self._pattern_template_unpack.fullmatch(elem):
                    out.extend(elem_filled)
                else:
                    out.append(elem_filled)
            return out
        if isinstance(templ, dict):
            new_dict = {}
            for key, val in templ.items():
                key_filled = self._recursive_subst(
                    templ=key, current_path=current_path, always_list=False, relative_path_anchor=relative_path_anchor,
                )
                if key_filled in self._template_keys:
                    new_dict[key_filled] = val
                    continue
                new_path = f"{current_path}.'{key_filled}'"
                new_dict[key_filled] = self._recursive_subst(
                    templ=val, current_path=new_path, always_list=always_list, relative_path_anchor=get_relative_path(new_path),
                )
            return new_dict
        return templ

    @staticmethod
    def _remove_leading_periods(s: str) -> (str, int):
        match = _re.match(r"^(\.*)(.*)", s)
        if match:
            leading_periods = match.group(1)
            rest_of_string = match.group(2)
            num_periods = len(leading_periods)
        else:
            num_periods = 0
            rest_of_string = s
        return rest_of_string, num_periods

    @staticmethod
    def _extract_fields(jsonpath):
        def _recursive_extract(expr):
            if hasattr(expr, "fields"):
                fields.extend(expr.fields)
            if hasattr(expr, "right"):
                _recursive_extract(expr.right)
            if hasattr(expr, "left"):
                _recursive_extract(expr.left)
            return
        fields = []
        _recursive_extract(jsonpath)
        return fields