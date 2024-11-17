class PropertyDict:

    def __init__(self, data: dict | None):
        self._data = data or {}
        return

    @property
    def as_dict(self) -> dict:
        """The data as a dictionary."""
        return self._data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, default=None):
        return self._data.pop(key, default)

    def setdefault(self, key, default):
        return self._data.setdefault(key, default)

    def __getattr__(self, name: str):
        return self._data[name]

    def __getitem__(self, name: str):
        return self._data[name]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, name: str):
        return name in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"PropertyDict({self._data})"

    def __str__(self):
        return str(self._data)

    def __eq__(self, other):
        return self._data == other._data

    def __ne__(self, other):
        return self._data != other._data
