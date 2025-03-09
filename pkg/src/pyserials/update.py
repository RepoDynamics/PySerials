from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING
import re as _re
from functools import partial as _partial

import jsonpath_ng as _jsonpath
from jsonpath_ng import exceptions as _jsonpath_exceptions

import pyserials.exception as _exception

if _TYPE_CHECKING:
    from typing import Literal, Sequence, Any, Callable, Iterable
    UPDATE_OPTIONS = Literal["skip", "write", "raise"] | Callable[
        [tuple[Any] | tuple[Any, Any]], None | tuple[Any, str]
    ]
    FUNC_ITEMS = Callable[[Any], Iterable[tuple[Any, Any]]]
    FUNC_CONTAINS = Callable[[Any, Any], bool]
    FUNC_GET = Callable[[Any, Any], Any]
    FUNC_SET = Callable[[Any, Any, Any], None]
    FUNC_CONSTRUCT = Callable[[], Any]
    RECURSIVE_DTYPE_FUNCS = tuple[FUNC_ITEMS, FUNC_CONTAINS, FUNC_GET, FUNC_SET, FUNC_CONSTRUCT]


def recursive_update(
    source: Any,
    addon: Any,
    recursive_types: dict[type | tuple[type, ...], RECURSIVE_DTYPE_FUNCS] | None = None,
    types: dict[type | tuple[type, ...], UPDATE_OPTIONS | tuple[UPDATE_OPTIONS, UPDATE_OPTIONS]] | None = None,
    paths: dict[str, UPDATE_OPTIONS] | None = None,
    constructor: Callable[[], Any] | None = None,
    undefined_new: UPDATE_OPTIONS = "write",
    undefined_existing: UPDATE_OPTIONS = "skip",
    type_mismatch: UPDATE_OPTIONS = "raise",
) -> dict[str, list[str]]:
    """Recursively update a complex data structure using another data structure.

    Parameters
    ----------
    source
        Data structure to update in place.
        The type of this object must be
        defined in the `recursive_types` argument.
    addon
        Data structure containing additional data to update `source` with.
    recursive_types
        Definition of recursive data types.
        Each key is a type (or tuple of types) used
        to identify data types with the `isinstance` function.
        Each value is a tuple of three functions:
        1. Function to extract items from the data. It must accept an instance
           of the type and return an iterable of key-value pairs.
        2. Function to check if a key is in the data. It must accept an instance
           of the type and a key, and return a boolean.
        3. Function to get a value from the data. It must accept an instance
           of the type and a key, and return the value.
        4. Function to set a key-value pair in the data. It must accept an instance
           of the type, a key, and a value, respectively.
        5. Function to construct a new instance of the type. It must accept no arguments.

        By default, `dict` is defined as follows:
        ```python
        recursive_types = {
            dict: (
                lambda dic: dic.items(),
                lambda dic, key: key in dic,
                lambda dic, key: dic[key],
                lambda dic, key, value: dic.update({key: value}),
                lambda: dict(),
            )
        }
        ```
        This default argument will be updated/overwritten with any custom types provided.
        For example, to add support for a custom class `MyClass`, you can use:
        ```python
        recursive_types = {
            MyClass: (
                lambda obj: vars(object).items(),
                lambda obj, key: hasattr(obj, key),
                lambda obj, key: getattr(obj, key),
                lambda obj, key, value: setattr(obj, key, value),
                lambda: MyClass(),
            )
        }
        ```
    types
        Update behavior for specific data types.
        Each key is a type (or tuple of types) used
        to identify data types with the `isinstance` function.
        Each value is can be single update option for all cases,
        or a tuple of two update options for when the corresponding
        key/attribute does not exist in the source data, and when it does, respectively.
        Each update option can be either a keyword specifying a predefined behavior,
        or a function for custom behavior. The available keywords are:
        - "skip": Ignore the key/attribute; do not change anything.
        - "write": Write the key/attribute in source data with the value from the addon, overwriting if it exists.

        A custom function must accept a single argument, a tuple of either one or two values.
        If it is two values, the first value is the current value in the source data,
        and the second value is the value from the addon.
        If it is one value, the value is the value from the addon,
        meaning the key/attribute does not exist in the source data.
        The function must either return `None` (for when nothing must be changes in the source)
        or a tuple of two values:
        1. The new value to write in the source data.
        2. A string specifying the change type.

        By default, the following behavior is defined for basic types:
        ```python
        types = {list: ("write", lambda data: (data[0] + data[1], "append"))}
        ```

        The default behavior for any data type not specified in this argument
        is determined by the `undefined_new` and `undefined_existing` arguments.
    paths
        Update behavior for specific keys using JSONPath expressions.
        This is the same as the `types` argument, but targeting specific keys
        instead of data types.
        Everything is the same as in the `types` argument, except that the keys
        are JSONPath expressions as strings.
    constructor
        Custom constructor for creating new instances of the source data type.
        This is used when the addon data contains a recursive key/attribute
        that is not present in the source data. If not provided,
        the type of the addon value will be used to create a new instance.
    undefined_new
        Behavior for when a non-recursive data with no defined behavior
        in the `types` argument is found in the addon data
        but not in the source data.
    undefined_existing
        Behavior for when a non-recursive data with no defined behavior
        in the `types` argument is found in the addon data
        and in the source data.
    type_mismatch
        Behavior for when a key/attribute in the source data
        is not a recursive type, but the corresponding key/attribute
        in the addon data is a recursive type.
    """
    def get_funcs(data: Any) -> RECURSIVE_DTYPE_FUNCS | None:
        for typ, funcs in recursive_types.items():
            if isinstance(data, typ):
                return funcs
        return None

    def recursive(
        src: Any,
        add: Any,
        src_funcs: RECURSIVE_DTYPE_FUNCS,
        add_funcs: RECURSIVE_DTYPE_FUNCS,
        path: str,
    ):

        def apply(behavior: UPDATE_OPTIONS | tuple[UPDATE_OPTIONS, UPDATE_OPTIONS]):
            action = behavior[int(key_exists_in_src)] if isinstance(behavior, tuple) else behavior
            if action == "raise":
                raise_error(typ="duplicate")
            elif action == "skip":
                change_type = "skip"
            elif action == "write":
                change_type = "write"
                fn_src_set(src, key, value)
            elif not isinstance(action, str):
                out = action((source_value, value) if key_exists_in_src else (value,))
                if out:
                    new_value, change_type = out
                    fn_src_set(src, key, new_value)
                else:
                    change_type = "skip"
            else:
                raise ValueError(f"Invalid update behavior '{action}' for key '{key}' at path '{path}'.")
            log[fullpath] = (type(source_value) if key_exists_in_src else None, type(value), change_type)
            return

        def raise_error(typ: Literal["duplicate", "type_mismatch"]):
            raise _exception.update.PySerialsUpdateRecursiveDataError(
                problem_type=typ,
                path=fullpath,
                data=src[key],
                data_full=src,
                data_addon=value,
                data_addon_full=addon,
            )

        _, fn_src_contains, fn_src_get, fn_src_set, _ = src_funcs
        fn_add_items, _, _, _, fn_add_construct = add_funcs

        for key, value in fn_add_items(add):
            fullpath = f"{path}.'{key}'"
            try:
                full_jpath = _jsonpath.parse(fullpath)  # quote to avoid JSONPath syntax errors
            except Exception as e:
                print(fullpath)
                raise e
            key_exists_in_src = fn_src_contains(src, key)
            source_value = fn_src_get(src, key) if key_exists_in_src else None
            for jpath_str, matches in jsonpath_match.items():
                if full_jpath in matches:
                    apply(paths[jpath_str])
                    break
            else:
                for typ, action in type_to_arg.items():
                    if isinstance(value, typ):
                        apply(action)
                        break
                else:
                    funcs_value = get_funcs(value)
                    if funcs_value:
                        # Value is a recursive type
                        if key_exists_in_src:
                            funcs_src_value = get_funcs(source_value)
                            if not funcs_src_value:
                                # Source value is not a recursive type
                                apply(type_mismatch)
                            else:
                                recursive(
                                    src=fn_src_get(src, key),
                                    add=value,
                                    path=fullpath,
                                    src_funcs=src_funcs,
                                    add_funcs=funcs_value,
                                )
                        else:
                            # Source value does not exist; create a new instance
                            new_instance = constructor() if constructor else fn_add_construct()
                            fn_src_set(src, key, new_instance)
                            funcs_src_value = get_funcs(new_instance)
                            recursive(
                                src=new_instance,
                                add=value,
                                path=fullpath,
                                src_funcs=funcs_src_value,
                                add_funcs=funcs_value,
                            )
                    else:
                        # addon value is of a non-recursive type that does not have any defined behavior;
                        # Apply the default behavior for of ("write", "skip") for the key.
                        apply(undefined_existing if key_exists_in_src else undefined_new)
        return

    type_to_arg = {list: ("write", lambda data: (data[0] + data[1], "append"))} | (types or {})
    recursive_types = {
        dict: (
            lambda dic: dic.items(),
            lambda dic, key: key in dic,
            lambda dic, key: dic[key],
            lambda dic, key, value: dic.update({key: value}),
            lambda: dict(),
        )
    } | (recursive_types or {})
    jsonpath_match = {
        jpath_str: [match.full_path for match in _jsonpath.parse(jpath_str).find(addon)]
        for jpath_str in (paths or {}).keys()
    }
    log = {}
    funcs_src = get_funcs(source)
    funcs_add = get_funcs(addon)
    for funcs, param_name, data in ((funcs_src, "source", source), (funcs_add, "addon", addon)):
        if not funcs:
            raise ValueError(f"Data type '{type(data)}' of '{param_name}' is not provided in 'recursive_types'.")
    recursive(
        src=source,
        add=addon,
        path="$",
        src_funcs=funcs_src,
        add_funcs=funcs_add,
    )
    return log


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
        relative_key_key: str | None = None,
        implicit_root: bool = True,
        getter_function_name: str = "get",
        skip_key_func: Callable[[list[str]], bool] | None = None,
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
        self._relative_key_key = relative_key_key
        self._getter_function_name = getter_function_name
        self._skip_func = skip_key_func

        self._pattern_value: dict[int, _RegexPattern] = {}
        self._data = None
        self._visited_paths = {}
        return

    def fill(
        self,
        data: dict | list,
        template: dict | list | str | None = None,
        current_path: str = "",
    ):
        self._data = data
        self._visited_paths = {}
        path = _jsonpath.parse((f"$.{current_path}" if self._add_prefix else current_path) if current_path else "$")
        return self._recursive_subst(
            templ=template or data,
            current_path=path,
            relative_path_anchor=path,
            level=0,
            current_chain=(path,),
        )

    def _recursive_subst(self, templ, current_path: str, relative_path_anchor: str, level: int, current_chain: tuple[str, ...], is_key: bool = False):

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
            global_context = self._code_context.copy() | {
                self._getter_function_name: getter_function,
                "__current_path__": current_path,
                "__relative_path_anchor__": relative_path_anchor
            }
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
                output = local_context["__inline_code__"]()
            except Exception as e:
                raise_error(
                    description_template=f"Code at {{path_invalid}} raised an exception: {e}\n{code_str_full}",
                    path_invalid=current_path,
                    exception=e,
                )
            return output

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
                    anchor_path = relative_path_anchor if is_relative_template else current_path
                else:
                    anchor_path = current_path
                root_path_expr = anchor_path
                for period in range(num_periods):
                    if isinstance(root_path_expr, _jsonpath.Root):
                        raise_error(
                            path_invalid=path_expr,
                            description_template=(
                                "Relative path {path_invalid} is invalid; "
                                f"reached root but still {num_periods - period} levels remaining."
                            ),
                        )
                    root_path_expr = root_path_expr.left
                # Handle relative-key key
                if self._relative_key_key and path == self._relative_key_key:
                    output = root_path_expr.right
                    if isinstance(output, _jsonpath.Fields):
                        output = output.fields[0]
                    elif isinstance(output, _jsonpath.Index):
                        output = output.index
                    if from_code:
                        return output, True
                    return output
                path_expr = self._concat_json_paths(root_path_expr, path_expr)
            # print("IN GET ADD VAL", path_expr)
            cached_result = self._visited_paths.get(path_expr)
            if cached_result:
                value, matched = cached_result
            else:
                value, matched = get_value(path_expr, return_all_matches, from_code)
            if not self._is_relative_template(path_expr):
                self._visited_paths[path_expr] = (value, matched)
            if from_code:
                return value, matched
            if matched:
                return value
            if self._leave_no_match:
                return match.group()
            return self._no_match_value

        def get_value(jsonpath, return_all_matches: bool, from_code: bool) -> tuple[Any, bool]:
            matches = recursive_match(jsonpath)
            if not matches:
                if from_code:
                    return None, False
                if return_all_matches:
                    return [], True
                if self._raise_no_match:
                    raise_error(
                        path_invalid=jsonpath,
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
                current_path=jsonpath,
                relative_path_anchor=_rel_path_anchor,
                level=0,
                current_chain=current_chain + (jsonpath,),
            ), True

        def recursive_match(expr) -> list:
            matches = expr.find(self._data)
            if matches:
                return matches
            if isinstance(expr.left, _jsonpath.Root):
                return []
            whole_matches = []
            left_matches = recursive_match(expr.left)
            for left_match in left_matches:
                left_match_filled = self._recursive_subst(
                    templ=left_match.value,
                    current_path=expr.left,
                    relative_path_anchor=expr.left,
                    level=0,
                    current_chain=current_chain + (expr.left,),
                ) if isinstance(left_match.value, str) else left_match.value
                right_matches = expr.right.find(left_match_filled)
                whole_matches.extend(right_matches)
            return whole_matches

        def get_relative_path(new_path):
            return new_path if current_path == relative_path_anchor else relative_path_anchor

        def fill_nested_values(match: _re.Match | str):
            pattern_nested = self._get_value_regex_pattern(level=level + 1)
            return pattern_nested.sub(
                lambda x: str(
                    self._recursive_subst(
                        templ=x.group(),
                        current_path=current_path,
                        relative_path_anchor=get_relative_path(current_path),
                        level=level + 1,
                        current_chain=current_chain,
                    )
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

        def raise_error(path_invalid: str, description_template: str, exception: Exception | None = None):
            raise _exception.update.PySerialsUpdateTemplatedDataError(
                description_template=description_template,
                path_invalid=path_invalid,
                path=current_path,
                data=templ,
                data_full=self._data,
                data_source=self._data,
                template_start=self._marker_start_value,
                template_end=self._marker_end_value,
            ) from exception

        # print("IN MAIN", self._extract_fields(current_path))

        if self._skip_func and self._skip_func(self._extract_fields(current_path)):
            return templ

        if current_path in self._visited_paths:
            return self._visited_paths[current_path][0]

        self._check_endless_loop(templ, current_chain)
        is_relative_template = self._is_relative_template(current_path)

        if isinstance(templ, str):
            # Handle value blocks
            pattern_value = self._get_value_regex_pattern(level=level)
            if match_value := pattern_value.fullmatch(templ):
                out = get_address_value(fill_nested_values(match_value))
            # Handle list blocks
            elif match_list := self._pattern_list.fullmatch(templ):
                out = get_address_value(fill_nested_values(match_list), return_all_matches=True)
            # Handle code blocks
            elif match_code := self._pattern_code.fullmatch(templ):
                out = get_code_value(match_code)
            # Handle unpack blocks
            elif match_unpack := self._pattern_unpack.fullmatch(templ):
                unpack_value = match_unpack.group(1)
                if submatch_code := self._pattern_code.fullmatch(unpack_value):
                    out = get_code_value(submatch_code)
                else:
                    unpack_value = fill_nested_values(unpack_value)
                    if submatch_list := self._pattern_list.fullmatch(unpack_value):
                        out = get_address_value(submatch_list, return_all_matches=True)
                    else:
                        out = get_address_value(unpack_value)
            # Handle strings
            else:
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
                out = pattern_value.sub(
                    lambda x: self._stringer(get_address_value(x)),
                    lists_filled
                )
            if not is_relative_template and not is_key:
                self._visited_paths[current_path] = (out, True)
            return out

        if isinstance(templ, list):
            out = []
            for idx, elem in enumerate(templ):
                new_path = _jsonpath.Child(current_path, _jsonpath.Index(idx))
                elem_filled = self._recursive_subst(
                    templ=elem,
                    current_path=new_path,
                    relative_path_anchor=get_relative_path(new_path),
                    level=0,
                    current_chain=current_chain + (new_path,),
                )
                if isinstance(elem, str) and self._pattern_unpack.fullmatch(elem):
                    try:
                        out.extend(elem_filled)
                    except TypeError as e:
                        raise_error(
                            path_invalid=current_path,
                            description_template=str(e)
                        )
                else:
                    out.append(elem_filled)
            if not is_relative_template:
                self._visited_paths[current_path] = (out, True)
            return out

        if isinstance(templ, dict):
            new_dict = {}
            addons = []
            for key, val in templ.items():
                key_filled = self._recursive_subst(
                    templ=key,
                    current_path=current_path,
                    relative_path_anchor=relative_path_anchor,
                    level=0,
                    current_chain=current_chain,
                    is_key=True,
                )
                if isinstance(key, str) and self._pattern_unpack.fullmatch(key):
                    addons.append((key_filled, val))
                    continue
                if key_filled in self._template_keys:
                    new_dict[key_filled] = val
                    continue
                new_path = _jsonpath.Child(current_path, _jsonpath.Fields(key_filled))
                new_dict[key_filled] = self._recursive_subst(
                    templ=val,
                    current_path=new_path,
                    relative_path_anchor=get_relative_path(new_path),
                    level=0,
                    current_chain=current_chain + (new_path,),
                )
            for addon_dict, addon_settings in sorted(
                addons, key=lambda addon: addon[1].get("priority", 0) if addon[1] else 0
            ):
                addon_settings = {k: v for k, v in (addon_settings or {}).items() if k not in ("priority",)}
                recursive_update(
                    source=new_dict,
                    addon=addon_dict,
                    **addon_settings,
                )
            if not is_relative_template:
                self._visited_paths[current_path] = (new_dict, True)
            return new_dict
        return templ

    def _check_endless_loop(self,templ, chain: tuple[str, ...]):
        last_idx = len(chain) - 1
        first_idx = chain.index(chain[-1])
        if first_idx == last_idx:
            return
        loop = [chain[-2], *chain[first_idx: -2]]
        loop_str = "\n".join([f"- {path}" for path in loop])
        history_str = "\n".join([f"- {path}" for path in chain])
        raise _exception.update.PySerialsUpdateTemplatedDataError(
            description_template=f"Path {{path_invalid}} starts a loop:\n{loop_str}\nHistory:\n{history_str}",
            path_invalid=chain[-2],
            path=chain[0],
            data=templ,
            data_full=self._data,
            data_source=self._data,
            template_start=self._marker_start_value,
            template_end=self._marker_end_value,
        )

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

    def _is_relative_template(self, jsonpath):
        path_fields = self._extract_fields(jsonpath)
        return any(field in self._template_keys for field in path_fields)

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

    @staticmethod
    def _normalize_path(path: str) -> str:
        return path.replace("'", "")

    def _concat_json_paths(self, path1, path2):
        if not isinstance(path2, _jsonpath.Child):
            return _jsonpath.Child(path1, path2)
        return _jsonpath.Child(self._concat_json_paths(path1, path2.left), path2.right)

class _RegexPattern:

    def __init__(self, start: str, end: str):
        start_esc = _re.escape(start)
        end_esc = _re.escape(end)
        self.pattern = _re.compile(rf"{start_esc}(.*?)(?={end_esc}){end_esc}", _re.DOTALL)
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

