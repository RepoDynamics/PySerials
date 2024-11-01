from __future__ import annotations as _annotations

import re
from typing import TYPE_CHECKING as _TYPE_CHECKING
import re as _re
from functools import partial as _partial

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
        raise_no_match: bool = True,
        leave_no_match: bool = False,
        no_match_value: Any = None,
        code_context: dict[str, Any] | None = None,
        code_context_partial: dict[str, Callable | tuple[Callable, str]] | None = None,
        code_context_call: dict[str, Callable[[Callable], Any]] | None = None,
        stringer: Callable[[str], str] = str,
        unpack_string_joiner: str = ", ",
        relative_template_keys: list[str] | None = None,
        implicit_root: bool = True,
        getter_function_name: str = "get",
    ):
        self._marker_start_value = marker_start_value
        self._marker_end_value = marker_end_value
        self._repeater_start_value = repeater_start_value
        self._repeater_end_value = repeater_end_value
        self._repeater_count_value = repeater_count_value
        self._pattern_list = _RegexPattern(start=start_list, end=end_list)
        self._pattern_unpack = _RegexPattern(start=start_unpack, end=end_unpack)
        self._pattern_code = _RegexPattern(start=start_code, end=end_code)

        self._raise_no_match = raise_no_match
        self._leave_no_match = leave_no_match
        self._no_match_value = no_match_value
        self._code_context = code_context or {}
        self._code_context_partial = code_context_partial or {}
        self._code_context_call = code_context_call or {}
        self._stringer = stringer
        self._unpack_string_joiner = unpack_string_joiner
        self._add_prefix = implicit_root
        self._template_keys = relative_template_keys or []
        self._getter_function_name = getter_function_name

        self._pattern_value: dict[int, _RegexPattern] = {}
        self._data = None
        return

    def fill(
        self,
        data: dict | list,
        template: dict | list | str | None = None,
        current_path: str = "",
    ):
        self._data = data
        path = (f"$.{current_path}" if self._add_prefix else current_path) if current_path else "$"
        return self._recursive_subst(
            templ=template or data,
            current_path=path,
            relative_path_anchor=path,
            level=0,
            current_chain=[path],
        )

    def _recursive_subst(self, templ, current_path: str, relative_path_anchor: str, level: int, current_chain: list[str]):

        def get_code_value(match: _re.Match | str):

            def getter_function(path: str, default: Any = None, search: bool = False):
                value, matched = get_address_value(path, return_all_matches=search, from_code=True)
                if matched:
                    return value
                if search:
                    return []
                return default

            code_str = match if isinstance(match, str) else match.group(1)
            code_lines = ["def __inline_code__():"]
            code_lines.extend([f"    {line}" for line in code_str.strip("\n").splitlines()])
            code_str_full = "\n".join(code_lines)
            global_context = self._code_context.copy() | {self._getter_function_name: getter_function}
            for name, partial_func_data in self._code_context_partial.items():
                if isinstance(partial_func_data, tuple):
                    func, arg_name = partial_func_data
                    global_context[name] = _partial(func, **{arg_name: getter_function})
                else:
                    global_context[name] = _partial(partial_func_data, getter_function)
            for name, call_func in self._code_context_call.items():
                global_context[name] = call_func(getter_function)
            local_context = {}
            try:
                exec(code_str_full, global_context, local_context)
                return local_context["__inline_code__"]()
            except Exception as e:
                raise_error(
                    description_template=f"Code at {{path_invalid}} raised an exception: {e}\n{code_str_full}",
                    path_invalid=current_path,
                )

        def get_address_value(match: _re.Match | str, return_all_matches: bool = False, from_code: bool = False):
            raw_path = match if isinstance(match, str) else str(match.group(1))
            path, num_periods = self._remove_leading_periods(raw_path.strip())
            if num_periods == 0:
                path = f"$.{path}" if self._add_prefix else path
            try:
                path_expr = _jsonpath.parse(path)
            except _jsonpath_exceptions.JSONPathError:
                raise_error(
                    path_invalid=path,
                    description_template="JSONPath expression {path_invalid} is invalid.",
                )
            if num_periods:
                if relative_path_anchor != current_path:
                    path_fields = self._extract_fields(_jsonpath.parse(current_path))
                    has_template_key = any(field in self._template_keys for field in path_fields)
                    anchor_path = relative_path_anchor if has_template_key else current_path
                else:
                    anchor_path = current_path
                root_path_expr = _jsonpath.parse(anchor_path)
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
                path_expr = self._concat_json_paths(root_path_expr, path_expr)
            value, matched = get_value(path_expr, return_all_matches, from_code)
            if from_code:
                return value, matched
            if matched:
                return value
            if self._leave_no_match:
                return match.group()
            return self._no_match_value

        def get_value(jsonpath, return_all_matches: bool, from_code: bool) -> tuple[Any, bool]:
            matches = _rec_match(jsonpath)
            if not matches:
                if from_code:
                    return None, False
                if return_all_matches:
                    return [], True
                if self._raise_no_match:
                    raise_error(
                        path_invalid=str(jsonpath),
                        description_template="JSONPath expression {path_invalid} did not match any data.",
                    )
                return None, False
            values = [m.value for m in matches]
            output = values if return_all_matches or len(values) > 1 else values[0]
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
                current_chain=current_chain + [str(jsonpath)],
            ), True

        def _rec_match(expr) -> list:
            matches = expr.find(self._data)
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
                    current_chain=current_chain + [str(expr.left)],
                ) if isinstance(left_match.value, str) else left_match.value
                right_matches = expr.right.find(left_match_filled)
                whole_matches.extend(right_matches)
            return whole_matches

        def get_relative_path(new_path):
            return new_path if current_path == relative_path_anchor else relative_path_anchor

        def fill_nested_values(match: _re.Match | str):
            pattern_nested = self._get_value_regex_pattern(level=level + 1)
            return pattern_nested.sub(
                lambda x: self._recursive_subst(
                    templ=x.group(),
                    current_path=current_path,
                    relative_path_anchor=get_relative_path(current_path),
                    level=level + 1,
                    current_chain=current_chain,
                ),
                match if isinstance(match, str) else match.group(1),
            )

        def string_filler_unpack(match: _re.Match):
            path = str(match.group(1)).strip()
            match_list = self._pattern_list.fullmatch(path)
            if match_list:
                values = get_address_value(match_list, return_all_matches=True)
            else:
                match_code = self._pattern_code.fullmatch(path)
                if match_code:
                    values = get_code_value(match_code)
                else:
                    values = get_address_value(path)
            return self._unpack_string_joiner.join([self._stringer(val) for val in values])

        def raise_error(path_invalid: str, description_template: str):
            raise _exception.update.PySerialsUpdateTemplatedDataError(
                description_template=description_template,
                path_invalid=path_invalid,
                path=current_path,
                data=templ,
                data_full=self._data,
                data_source=self._data,
                template_start=self._marker_start_value,
                template_end=self._marker_end_value,
            )

        # if not internal:
        #     self._path_history.append(current_path)
        # loop = self._find_loop()
        # if loop:
        #     loop_str = "\n".join([f"- {path.replace("'", "")}" for path in loop])
        #     raise _exception.update.PySerialsUpdateTemplatedDataError(
        #         description_template=f"Path {{path_invalid}} starts a loop: {loop_str}",
        #         path_invalid=loop[0],
        #         path=current_path,
        #         data=templ,
        #         data_full=self._data,
        #         data_source=self._source,
        #         template_start=self._marker_start_value,
        #         template_end=self._marker_end_value,
        #     )

        if isinstance(templ, str):
            # Handle value blocks
            pattern_value = self._get_value_regex_pattern(level=level)
            match_value = pattern_value.fullmatch(templ)
            if match_value:
                return get_address_value(fill_nested_values(match_value))
            # Handle list blocks
            match_list = self._pattern_list.fullmatch(templ)
            if match_list:
                return get_address_value(fill_nested_values(match_list), return_all_matches=True)
            # Handle code blocks
            match_code = self._pattern_code.fullmatch(templ)
            if match_code:
                return get_code_value(match_code)
            # Handle unpack blocks
            match_unpack = self._pattern_unpack.fullmatch(templ)
            if match_unpack:
                unpack_value = match_unpack.group(1)
                submatch_code = self._pattern_code.fullmatch(unpack_value)
                if submatch_code:
                    return get_code_value(submatch_code)
                unpack_value = fill_nested_values(unpack_value)
                submatch_list = self._pattern_list.fullmatch(unpack_value)
                if submatch_list:
                    return get_address_value(unpack_value, return_all_matches=True)
                return get_address_value(unpack_value)
            # Handle strings
            code_blocks_filled = self._pattern_code.sub(
                lambda x: self._stringer(get_code_value(x)),
                templ
            )
            nested_values_filled = fill_nested_values(code_blocks_filled)
            unpacked_filled = self._pattern_unpack.sub(string_filler_unpack, nested_values_filled)
            lists_filled = self._pattern_list.sub(
                lambda x: self._stringer(get_address_value(x)),
                unpacked_filled
            )
            templ_values_filled = pattern_value.sub(
                lambda x: self._stringer(get_address_value(x)),
                lists_filled
            )
            return templ_values_filled

        if isinstance(templ, list):
            out = []
            for idx, elem in enumerate(templ):
                new_path = f"{current_path}[{idx}]"
                elem_filled = self._recursive_subst(
                    templ=elem,
                    current_path=new_path,
                    relative_path_anchor=get_relative_path(new_path),
                    level=0,
                    current_chain=current_chain + [new_path],
                )
                if isinstance(elem, str) and self._pattern_unpack.fullmatch(elem):
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
                    current_chain=current_chain,
                )
                if isinstance(key, str) and self._pattern_unpack.fullmatch(key):
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
                    current_chain=current_chain + [new_path],
                )
            return new_dict
        return templ

    # def _find_loop(self):
    #     for pattern_length in range(1, len(self._path_history) // 2 + 1):
    #         # Slice the end of the list into two consecutive patterns
    #         pattern = self._path_history[-pattern_length:]
    #         previous_pattern = self._path_history[-2 * pattern_length:-pattern_length]
    #         # Check if the two patterns are the same
    #         if pattern == previous_pattern:
    #             pattern.insert(0, pattern[-1])
    #             return pattern
    #     return

    def _get_value_regex_pattern(self, level: int = 0) -> _RegexPattern:
        if level in self._pattern_value:
            return self._pattern_value[level]
        count = self._repeater_count_value + level
        pattern = _RegexPattern(
            start=f"{self._marker_start_value}{self._repeater_start_value * count} ",
            end=f" {self._repeater_end_value * count}{self._marker_end_value}",
        )
        self._pattern_value[level] = pattern
        return pattern

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

    def _concat_json_paths(self, path1, path2):
        if not isinstance(path2, _jsonpath.Child):
            return _jsonpath.Child(path1, path2)
        return _jsonpath.Child(self._concat_json_paths(path1, path2.left), path2.right)

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
            return self.pattern.fullmatch(string.strip())
        return None

    def sub(self, repl, string: str) -> str:
        return self.pattern.sub(repl, string)
