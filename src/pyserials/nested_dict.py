from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING

import pyserials as _ps

if _TYPE_CHECKING:
    from typing import Callable, Any


class NestedDict:

    def __init__(
        self,
        data: dict | None = None,
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
        self._data = data or {}
        self._templater = _ps.update.TemplateFiller(
            marker_start_value=marker_start_value,
            marker_end_value=marker_end_value,
            repeater_start_value=repeater_start_value,
            repeater_end_value=repeater_end_value,
            repeater_count_value=repeater_count_value,
            start_list=start_list,
            start_unpack=start_unpack,
            start_code=start_code,
            end_list=end_list,
            end_unpack=end_unpack,
            end_code=end_code,
            raise_no_match=raise_no_match,
            leave_no_match=leave_no_match,
            no_match_value=no_match_value,
            code_context=code_context,
            code_context_partial=code_context_partial,
            code_context_call=code_context_call,
            stringer=stringer,
            unpack_string_joiner=unpack_string_joiner,
            relative_template_keys=relative_template_keys,
            implicit_root=implicit_root,
            getter_function_name=getter_function_name,
        )
        return

    def fill(self, path: str = ""):
        if not path:
            value = self._data
        else:
            value = self.__getitem__(path)
        if not value:
            return
        filled_value = self.fill_data(
            data=value,
            current_path=path,
        )
        if not path:
            self._data = filled_value
        else:
            self.__setitem__(path, filled_value)
        return filled_value

    def fill_data(self, data, current_path: str = ""):
        return self._templater.fill(
            data=self._data,
            template=data,
            current_path=current_path,
        )

    def __call__(self):
        return self._data

    def __getitem__(self, item: str):
        keys = item.split(".")
        data = self._data
        for key in keys:
            if not isinstance(data, dict):
                raise KeyError(f"Key '{key}' not found in '{data}'.")
            if key not in data:
                return
            data = data[key]
        # if isinstance(data, dict):
        #     return NestedDict(data)
        # if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        #     return [NestedDict(item) for item in data]
        return data

    def __setitem__(self, key, value):
        key = key.split(".")
        data = self._data
        for k in key[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        data[key[-1]] = value
        return

    def __contains__(self, item):
        keys = item.split(".")
        data = self._data
        for key in keys:
            if not isinstance(data, dict) or key not in data:
                return False
            data = data[key]
        return True

    def __bool__(self):
        return bool(self._data)

    def setdefault(self, key, value):
        key = key.split(".")
        data = self._data
        for k in key[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        return data.setdefault(key[-1], value)

    def get(self, key, default=None):
        keys = key.split(".")
        data = self._data
        for key in keys:
            if not isinstance(data, dict) or key not in data:
                return default
            data = data[key]
        return data

    def items(self):
        return self._data.items()

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def update(self, data: dict):
        self._data.update(data)
        return
