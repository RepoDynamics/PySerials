from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING

import pyserials as _ps

if _TYPE_CHECKING:
    from typing import Callable


class NestedDict:

    def __init__(
        self,
        data: dict | None = None,
        template_marker_start: str = "${{",
        template_marker_end: str = "}}",
        template_marker_unpack_start: str = "*{{",
        template_marker_unpack_end: str = "}}",
        template_implicit_root: bool = True,
        template_stringer: Callable[[str], str] = None,
        template_ignore_key_regex: str | None = None,
    ):
        self._data = data or {}
        self._templater = _ps.update.TemplateFiller(
            marker_start=template_marker_start,
            marker_end=template_marker_end,
            marker_unpack_start=template_marker_unpack_start,
            marker_unpack_end=template_marker_unpack_end,
            implicit_root=template_implicit_root,
            stringer=template_stringer,
        )
        self._ignore_key_regex = template_ignore_key_regex
        return

    def fill(
        self,
        path: str = "",
        always_list: bool = False,
        recursive: bool = True,
    ):
        if not path:
            value = self._data
        else:
            value = self.__getitem__(path)
        if not value:
            return
        filled_value = self.fill_data(
            data=value, current_path=path, always_list=always_list, recursive=recursive,
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
        always_list: bool = False,
        recursive: bool = True,
    ):
        return self._templater.fill(
            templated_data=data,
            source_data=self._data,
            current_path=current_path,
            always_list=always_list,
            recursive=recursive,
            ignore_key_regex=self._ignore_key_regex,
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
