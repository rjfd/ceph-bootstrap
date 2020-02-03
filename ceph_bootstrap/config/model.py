from collections import defaultdict

from typing import Dict, List, Any, Union


class ModelStoreListener:
    def model_store(self, new_value: Any) -> None:
        pass


class ModelLoadListener:
    def model_load(self) -> Any:
        pass


class CephSaltConfigModel:
    def __init__(self):
        self.store_listeners_map: Dict[str, List[ModelStoreListener]] = defaultdict(list)
        self.load_listeners_map: Dict[str, ModelLoadListener] = {}
        self.model_tree = None

    def add_listener(self, listener: Union[ModelStoreListener, ModelLoadListener], key: str = None):
        if key is None:
            key = ""
        if isinstance(listener, ModelStoreListener):
            self.store_listeners_map[key].append(listener)
        if isinstance(listener, ModelLoadListener):
            self.load_listeners_map[key] = listener

    def __setitem__(self, key, value):
        if not key:
            raise KeyError('key must not be empty nor None')
        if not isinstance(key, str):
            raise ValueError('key must be of str type')

        if self.model_tree is None:
            self.model_tree = _ModelDict(self)

        _dict = self.model_tree
        key_path = []
        while True:
            keys = key.split(':', 1)
            key_path.append(keys[0])
            if len(keys) > 1:
                if keys[0] not in _dict:
                    _dict[keys[0]] = _ModelDict(self, _dict, keys[0])
                _dict = _dict[keys[0]]
                if isinstance(_dict, dict):
                    key = keys[1]
                    continue
                raise ValueError("'{}' is not a dict".format(':'.join(key_path)))

            if isinstance(value, list):
                value = _ModelList(self, _dict, keys[0], value)
            elif isinstance(value, dict):
                value = _ModelDict(self, _dict, keys[0], value)
            _dict[keys[0]] = value
            return

    def __getitem__(self, key):
        if not key:
            raise KeyError('key must not be empty nor None')
        if not isinstance(key, str):
            raise ValueError('key must be of str type')

        if self.model_tree is None:
            self.model_tree = _ModelDict(self)

        _dict = self.model_tree
        key_path = []
        while True:
            keys = key.split(':', 1)
            key_path.append(keys[0])
            if keys[0] not in _dict:  # this cond will trigger a load listener if exists
                raise KeyError("key '{}' does not exist".format(keys[0]))
            val = _dict[keys[0]]
            if len(keys) > 1:
                if isinstance(val, dict):
                    key = keys[1]
                    _dict = val
                    continue
                raise ValueError("'{}' is not a dict".format(':'.join(key_path)))
            return val

    def __contains__(self, key):
        if not key:
            raise KeyError('key must not be empty nor None')
        if not isinstance(key, str):
            raise ValueError('key must be of str type')
        try:
            val = self[key]  # pylint: disable=unused-variable
        except KeyError:
            return False
        return True


class _ModelDict(dict):
    def __init__(self, model: CephSaltConfigModel, parent: "_ModelDict" = None, key: str = None,
                 _dict: dict = None):
        super(_ModelDict, self).__init__()
        self._model = model
        self._parent = parent
        self._key = key
        if _dict is not None:
            self.update(_dict)
        else:
            self._call_load_listeners()

    def _full_key(self):
        # pylint: disable=protected-access
        if self._key is None:
            return None
        if self._parent._key is None:
            return self._key
        return "{}:{}".format(self._parent._full_key(), self._key)

    def _call_parent_store_listeners(self, key, val):
        new_dict = dict()
        new_dict.update(self)
        new_dict[key] = val

        if self._parent is None:
            for listener in self._model.store_listeners_map['']:
                listener.model_store(new_dict)
            return

        # pylint: disable=protected-access
        self._parent._call_store_listeners(self._key, new_dict)

    def _call_store_listeners(self, key, val):
        fkey = self._full_key()
        if fkey is not None:
            fkey = "{}:{}".format(fkey, key)
        else:
            fkey = key
        for listener in self._model.store_listeners_map[fkey]:
            listener.model_store(val)
        self._call_parent_store_listeners(key, val)

    def _call_load_listeners(self, key=None):
        fkey = self._full_key()
        if fkey is not None:
            if key is not None:
                fkey = "{}:{}".format(fkey, key)
        else:
            fkey = key if key is not None else ''
        if fkey in self._model.load_listeners_map:
            val = self._model.load_listeners_map[fkey].model_load()
            if key is None:
                self.update(val, True)
            else:
                if isinstance(val, list):
                    val = _ModelList(self._model, self, key, val)
                elif isinstance(val, dict):
                    _dict = _ModelDict(self._model, self, key)
                    _dict.update(val, True)
                    val = _dict
                super(_ModelDict, self).__setitem__(key, val)

    def __setitem__(self, key, value):
        self._call_store_listeners(key, value)
        super(_ModelDict, self).__setitem__(key, value)

    def __getitem__(self, key):
        if not super(_ModelDict, self).__contains__(key):
            self._call_load_listeners(key)
        return super(_ModelDict, self).__getitem__(key)

    def __contains__(self, key):
        if not key:
            raise KeyError('key must not be empty nor None')
        if not isinstance(key, str):
            raise ValueError('key must be of str type')
        try:
            val = self[key]  # pylint: disable=unused-variable
        except KeyError:
            return False
        return True

    def update(self, _dict, from_load=False):
        if not isinstance(_dict, dict):
            raise ValueError('update argument must be a dict')
        for key, val in _dict.items():
            if isinstance(val, list):
                val = _ModelList(self._model, self, key, val)
            elif isinstance(val, dict):
                _dict_tmp = _ModelDict(self._model, self, key)
                _dict_tmp.update(val, from_load)
                val = _dict_tmp
            if from_load:
                super(_ModelDict, self).__setitem__(key, val)
            else:
                self[key] = val


class _ModelList(list):
    def __init__(self, model: CephSaltConfigModel, parent: _ModelDict, key: str, _list: list):
        self._model = None
        self._parent = parent
        super(_ModelList, self).__init__(_list)
        self._model = model
        self._key = key

    def _call_listeners(self, new_list):
        if self._model is None:
            return
        # pylint: disable=protected-access
        self._parent._call_store_listeners(self._key, new_list)

    def append(self, val):
        new_list = list(self)
        new_list.append(val)
        self._call_listeners(new_list)
        return super(_ModelList, self).append(val)

    def insert(self, idx, val):
        new_list = list(self)
        new_list.insert(idx, val)
        self._call_listeners(new_list)
        return super(_ModelList, self).insert(idx, val)

    def remove(self, val):
        new_list = list(self)
        new_list.remove(val)
        self._call_listeners(new_list)
        return super(_ModelList, self).remove(val)

    def pop(self, idx):
        new_list = list(self)
        new_list.pop(idx)
        self._call_listeners(new_list)
        return super(_ModelList, self).pop(idx)

    def clear(self):
        self._call_listeners([])
        return super(_ModelList, self).clear()
