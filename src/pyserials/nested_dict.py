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
        recursive: bool = True,
        raise_no_match: bool = True,
        leave_no_match: bool = False,
        no_match_value: Any = None,
        stringer: Callable[[str], str] = str,
        unpack_string_joiner: str = ", ",
        relative_template_keys: list[str] | None = None,
        implicit_root: bool = True,
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
        )
        self._recursive = recursive
        self._raise_no_match = raise_no_match
        self._leave_no_match = leave_no_match
        self._no_match_value = no_match_value
        self._stringer = stringer
        self._unpack_string_joiner = unpack_string_joiner
        self._relative_template_keys = relative_template_keys or []
        self._implicit_root = implicit_root
        return

    def fill(
        self,
        path: str = "",
        recursive: bool | None = None,
        raise_no_match: bool | None = None,
        leave_no_match: bool | None = None,
        stringer: Callable[[str], str] | None = None,
        unpack_string_joiner: str | None = None,
        level: int = 0,
    ):
        if not path:
            value = self._data
        else:
            value = self.__getitem__(path)
        if not value:
            return
        filled_value = self.fill_data(
            data=value,
            current_path=path,
            recursive=recursive,
            raise_no_match=raise_no_match,
            leave_no_match=leave_no_match,
            stringer=stringer,
            unpack_string_joiner=unpack_string_joiner,
            level=level,
        )
        if not path:
            self._data = filled_value
        else:
            self.__setitem__(path, filled_value)
        return filled_value

    def fill_data(
        self,
        data,
        current_path: str = "",
        recursive: bool | None = None,
        raise_no_match: bool | None = None,
        leave_no_match: bool | None = None,
        stringer: Callable[[str], str] | None = None,
        unpack_string_joiner: str | None = None,
        level: int = 0,
    ):
        return self._templater.fill(
            templated_data=data,
            source_data=self._data,
            current_path=current_path,
            recursive=recursive if recursive is not None else self._recursive,
            raise_no_match=raise_no_match if raise_no_match is not None else self._raise_no_match,
            leave_no_match=leave_no_match if leave_no_match is not None else self._leave_no_match,
            no_match_value=self._no_match_value,
            stringer=stringer if stringer is not None else self._stringer,
            unpack_string_joiner=unpack_string_joiner if unpack_string_joiner is not None else self._unpack_string_joiner,
            relative_template_keys=self._relative_template_keys,
            implicit_root=self._implicit_root,
            level=level,
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
