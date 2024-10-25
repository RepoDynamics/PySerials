from __future__ import annotations as _annotations

import re
from typing import TYPE_CHECKING as _TYPE_CHECKING
import re as _re

import jsonpath_ng as _jsonpath
from jsonpath_ng import exceptions as _jsonpath_exceptions

import pyserials.exception as _exception

if _TYPE_CHECKING:
    from typing import Literal, Sequence, Any, Callable


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
        marker_start_value: str = "$",
        marker_end_value: str = "$",
        repeater_start_value: str = "{",
        repeater_end_value: str = "}",
        repeater_count_value: int = 2,
        start_list: str = "$[[",
        start_unpack: str = "*{{",
        start_code: str = "#{{",
        end_list: str = "]]$",
        end_unpack: str = "}}*",
        end_code: str = "}}#",
    ):
        self._marker_start_value = marker_start_value
        self._marker_end_value = marker_end_value
        self._repeater_start_value = repeater_start_value
        self._repeater_end_value = repeater_end_value
        self._repeater_count_value = repeater_count_value
        self._pattern_list = _RegexPattern(start=start_list, end=end_list)
        self._pattern_unpack = _RegexPattern(start=start_unpack, end=end_unpack)
        self._pattern_code = _RegexPattern(start=start_code, end=end_code)
        self._add_prefix = True

        self._pattern_value: dict[int, _RegexPattern] = {}
        self._data = None
        self._source = None
        self._recursive = None
        self._path = None
        self._raise_no_match = None
        self._template_keys = None
        self._ignore_templates = True
        self._leave_no_match = False
        self._no_match_value = None
        self._stringer = str
        self._unpack_string_joiner = ", "
        return

    def _get_value_regex_pattern(self, level: int = 0) -> _RegexPattern:
        level_patterns = self._pattern_value.setdefault(level, {})
        if level in level_patterns:
            return level_patterns[level]
        count = self._repeater_count_value + level
        pattern = _RegexPattern(
            start=f"{self._marker_start_value}{self._repeater_start_value * count} ",
            end=f" {self._repeater_end_value * count}{self._marker_end_value}",
        )
        level_patterns[level] = pattern
        return pattern

    def fill(
        self,
        templated_data: dict | list | str,
        source_data: dict | list,
        current_path: str = "",
        recursive: bool = True,
        raise_no_match: bool = True,
        leave_no_match: bool = False,
        no_match_value: Any = None,
        stringer: Callable[[str], str] = str,
        unpack_string_joiner: str = ", ",
        relative_template_keys: list[str] | None = None,
        implicit_root: bool = True,
        level: int = 0,
    ):
        self._data = templated_data
        self._source = source_data
        self._recursive = recursive
        self._raise_no_match = raise_no_match
        self._leave_no_match = leave_no_match
        self._no_match_value = no_match_value
        self._stringer = stringer
        self._unpack_string_joiner = unpack_string_joiner
        self._add_prefix = implicit_root
        self._template_keys = relative_template_keys or []
        path = (f"$.{current_path}" if self._add_prefix else current_path) if current_path else "$"
        if not relative_template_keys:
            self._ignore_templates = False
            return self._recursive_subst(
                templ=self._data,
                current_path=path,
                relative_path_anchor=path,
                level=level,
            )
        self._ignore_templates = True
        first_pass = self._recursive_subst(
            templ=self._data,
            current_path=path,
            relative_path_anchor=path,
            level=level,
        )
        if self._data is self._source:
            self._source = first_pass
        self._data = first_pass
        self._ignore_templates = False
        return self._recursive_subst(
            templ=self._data,
            current_path=path,
            relative_path_anchor=path,
            level=level,
        )

    def _recursive_subst(self, templ, current_path: str, relative_path_anchor: str, level: int):

        def get_code_value(code_str: str):
            code_lines = ["def __inline_code__():"]
            code_lines.extend([f"    {line}" for line in code_str.strip("\n").splitlines()])
            code_str_full = "\n".join(code_lines)
            global_context = {}
            local_context = {}
            try:
                exec(code_str_full, global_context, local_context)
                return local_context["__inline_code__"]()
            except Exception as e:
                raise_error(
                    description_template=f"Code at {{path_invalid}} raised an exception: {e}\n{code_str_full}",
                    path_invalid=current_path,
                )

        def get_address_value(re_match, return_all_matches: bool = False):
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
            value, matched = get_value(path_expr, return_all_matches)
            if matched:
                return value
            if self._leave_no_match:
                return re_match.group()
            return self._no_match_value

        def get_value(jsonpath, return_all_matches: bool) -> tuple[Any, bool]:
            matches = _rec_match(jsonpath)
            if not matches:
                if not return_all_matches and self._raise_no_match:
                    raise_error(
                        path_invalid=str(jsonpath),
                        description_template="JSONPath expression {path_invalid} did not match any data.",
                    )
                return None, False
            values = [m.value for m in matches]
            output = values if return_all_matches or len(values) > 1 else values[0]
            if not self._recursive:
                return output, True
            if relative_path_anchor == current_path:
                path_fields = self._extract_fields(jsonpath)
                has_template_key = any(field in self._template_keys for field in path_fields)
                _rel_path_anchor = current_path if has_template_key else str(jsonpath)
            else:
                _rel_path_anchor = relative_path_anchor
            return self._recursive_subst(
                output,
                current_path=str(jsonpath),
                relative_path_anchor=_rel_path_anchor,
                level=0,
            ), True

        def _rec_match(expr) -> list:
            matches = expr.find(self._source)
            if matches:
                return matches
            if isinstance(expr.left, _jsonpath.Root):
                return []
            whole_matches = []
            left_matches = _rec_match(expr.left)
            for left_match in left_matches:
                left_match_filled = self._recursive_subst(
                    templ=left_match.value,
                    current_path=str(expr.left),
                    relative_path_anchor=str(expr.left),
                    level=0,
                ) if isinstance(left_match.value, str) else left_match.value
                right_matches = expr.right.find(left_match_filled)
                whole_matches.extend(right_matches)
            return whole_matches

        def get_relative_path(new_path):
            return new_path if current_path == relative_path_anchor else relative_path_anchor

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
                template_start=self._marker_start_value,
                template_end=self._marker_end_value,
            )

        def string_filler_unpack(match: _re.Match):
            match_list = self._pattern_list.fullmatch(match.group(1).strip())
            if match_list:
                values = get_address_value(match_list, return_all_matches=True)
            else:
                match_code = self._pattern_code.fullmatch(match.group(1).strip())
                if match_code:
                    values = get_code_value(match_code.group(1))
                else:
                    values = get_address_value(match)
            return self._unpack_string_joiner.join([self._stringer(val) for val in values])

        if isinstance(templ, str):
            pattern_nested = self._get_value_regex_pattern(level=level + 1)
            templ_nested_filled = pattern_nested.sub(
                lambda x: self._recursive_subst(
                    templ=x.group(),
                    current_path=current_path,
                    relative_path_anchor=get_relative_path(current_path),
                    level=level+1,
                ),
                templ
            )
            pattern_value = self._get_value_regex_pattern(level=level)
            whole_match_value = pattern_value.fullmatch(templ_nested_filled)
            if whole_match_value:
                return get_address_value(whole_match_value)
            templ_values_filled = pattern_value.sub(
                lambda x: str(get_address_value(x)),
                templ_nested_filled
            )
            whole_match_list = self._pattern_list.fullmatch(templ_values_filled.strip())
            if whole_match_list:
                return get_address_value(whole_match_list, return_all_matches=True)
            whole_match_unpack = self._pattern_unpack.fullmatch(templ_values_filled.strip())
            if whole_match_unpack:
                submatch_list = self._pattern_list.fullmatch(whole_match_unpack.group(1).strip())
                if submatch_list:
                    return get_address_value(submatch_list, return_all_matches=True)
                submatch_code = self._pattern_code.fullmatch(whole_match_unpack.group(1).strip())
                if submatch_code:
                    return get_code_value(submatch_code.group(1))
                return get_address_value(whole_match_unpack)
            whole_match_code = self._pattern_code.fullmatch(templ_values_filled.strip())
            if whole_match_code:
                templ_list_filled = self._pattern_list.sub(
                    lambda x: str(get_address_value(x, return_all_matches=True)),
                    whole_match_code.group(1)
                )
                return get_code_value(templ_list_filled)
            unpacked_filled = self._pattern_unpack.sub(string_filler_unpack, templ_values_filled)
            return self._pattern_code.sub(
                lambda x: self._stringer(get_code_value(x.group(1))),
                unpacked_filled
            )

        if isinstance(templ, list):
            out = []
            for idx, elem in enumerate(templ):
                new_path = f"{current_path}[{idx}]"
                elem_filled = self._recursive_subst(
                    templ=elem,
                    current_path=new_path,
                    relative_path_anchor=get_relative_path(new_path),
                    level=0,
                )
                if isinstance(elem, str) and self._pattern_unpack.fullmatch(elem.strip()):
                    out.extend(elem_filled)
                else:
                    out.append(elem_filled)
            return out

        if isinstance(templ, dict):
            new_dict = {}
            for key, val in templ.items():
                key_filled = self._recursive_subst(
                    templ=key,
                    current_path=current_path,
                    relative_path_anchor=relative_path_anchor,
                    level=0,
                )
                if isinstance(key, str) and self._pattern_unpack.fullmatch(key.strip()):
                    new_dict.update(key_filled)
                    continue
                if key_filled in self._template_keys:
                    new_dict[key_filled] = val
                    continue
                new_path = f"{current_path}.'{key_filled}'"
                new_dict[key_filled] = self._recursive_subst(
                    templ=val,
                    current_path=new_path,
                    relative_path_anchor=get_relative_path(new_path),
                    level=0,
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


class _RegexPattern:

    def __init__(self, start: str, end: str):
        start_esc = _re.escape(start)
        end_esc = _re.escape(end)
        self.pattern = _re.compile(rf"{start_esc}(.*?)(?={end_esc}){end_esc}", re.DOTALL)
        return

    def fullmatch(self, string: str) -> _re.Match | None:
        # Use findall to count occurrences of segments in the text
        matches = self.pattern.findall(string)
        if len(matches) == 1:
            # Verify the match spans the entire string
            return self.pattern.fullmatch(string)
        return None

    def sub(self, repl, string: str) -> str:
        return self.pattern.sub(repl, string)