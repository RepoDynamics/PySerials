import re as _re

import pyserials.exception as _exception


def dict_from_addon(
    data: dict,
    addon: dict,
    append_list: bool = True,
    append_dict: bool = True,
    raise_duplicates: bool = False,
) -> dict[str, list[str]]:
    """Recursively update a dictionary from another dictionary."""
    def recursive(source: dict, add: dict, path: str, log: dict):

        def raise_duplication_error():
            raise _exception.update.PySerialsDictUpdateDuplicationError(
                address=fullpath,
                value_data=source[key],
                value_addon=value,
            )

        for key, value in add.items():
            fullpath = f"{path}{key}"
            if key not in source:
                log["added"].append(fullpath)
                source[key] = value
                continue
            if type(source[key]) is not type(value):
                raise _exception.update.PySerialsDictUpdateTypeMismatchError(
                    address=fullpath,
                    value_data=source[key],
                    value_addon=value,
                )
            if not isinstance(value, (list, dict)):
                if raise_duplicates:
                    raise_duplication_error()
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
                    raise_duplication_error()
                else:
                    log["skipped"].append(fullpath)
            else:
                if append_dict:
                    recursive(source=source[key], add=value, path=f"{fullpath}.", log=log)
                elif raise_duplicates:
                    raise_duplication_error()
                else:
                    log["skipped"].append(fullpath)
        return log
    full_log = recursive(
        source=data, add=addon, path=".", log={"added": [], "skipped": [], "list_appended": []}
    )
    return full_log


def templated_data_from_source(
    templated_data: dict | list | str | bool | int | float,
    source_data: dict,
    template_start: str = "${{",
    template_end: str = "}}",
):
    filler = _TemplateFiller(
        templated_data=templated_data,
        source_data=source_data,
        template_start=template_start,
        template_end=template_end
    )
    return filler.fill()


class _TemplateFiller:

    def __init__(
        self,
        templated_data: dict | list | str | bool | int | float,
        source_data: dict,
        template_start: str,
        template_end: str,
    ):
        self._data = templated_data
        self._source = source_data
        self._template_start = template_start
        self._template_end = template_end
        marker_start = _re.escape(template_start)
        marker_end = _re.escape(template_end)
        self._pattern_template_whole = _re.compile(rf"^{marker_start}([\w\.\:\-\[\] ]+){marker_end}$")
        self._pattern_template_sub = _re.compile(rf"{marker_start}([\w\.\:\-\[\] ]+?){marker_end}")
        self._pattern_address_name = _re.compile(r"^([^[]+)")
        self._pattern_address_indices = _re.compile(r"\[([^]]+)]")
        return

    def fill(self):
        return self._recursive_subst(self._data)

    def _recursive_subst(self, value):
        if isinstance(value, str):
            match_whole_str = self._pattern_template_whole.match(value)
            if match_whole_str:
                return self._substitute_val(match_whole_str.group(1))
            return self._pattern_template_sub.sub(lambda x: str(self._substitute_val(x.group(1))), value)
        if isinstance(value, list):
            return [self._recursive_subst(elem) for elem in value]
        elif isinstance(value, dict):
            new_dict = {}
            for key, val in value.items():
                key_filled = self._recursive_subst(key)
                new_dict[key_filled] = self._recursive_subst(val)
            return new_dict
        return value

    def _substitute_val(self, match):
        def recursive_retrieve(obj, address):
            if len(address) == 0:
                return self._recursive_subst(obj)
            curr_add = address.pop(0)
            try:
                next_layer = obj[curr_add]
            except (TypeError, KeyError, IndexError) as e:
                try:
                    next_layer = self._recursive_subst(obj)[curr_add]
                except (TypeError, KeyError, IndexError):
                    raise _exception.update.PySerialsTemplateUpdateMissingSourceError(
                        address_full=address_full,
                        address_missing=curr_add,
                        templated_data=self._data,
                        source_data=self._source,
                        template_start=self._template_start,
                        template_end=self._template_end,
                    ) from e
            return recursive_retrieve(next_layer, address)

        address_full = match.strip()
        parsed_address = []
        for add in address_full.split("."):
            name = self._pattern_address_name.match(add).group()
            indices = self._pattern_address_indices.findall(add)
            parsed_address.append(name)
            parsed_ind = []
            for idx in indices:
                if ":" not in idx:
                    parsed_ind.append(int(idx))
                else:
                    slice_ = [int(i) if i else None for i in idx.split(":")]
                    parsed_ind.append(slice(*slice_))
            parsed_address.extend(parsed_ind)
        return recursive_retrieve(self._source, address=parsed_address)

