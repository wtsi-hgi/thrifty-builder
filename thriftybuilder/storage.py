import json
from abc import ABCMeta, abstractmethod
from typing import Optional, Dict

import os


class Storage(metaclass=ABCMeta):
    """
    TODO
    """
    @abstractmethod
    def get_checksum(self, configuration_id: str) -> Optional[str]:
        """
        TODO
        :param configuration_id:
        :return:
        """

    @abstractmethod
    def set_checksum(self, configuration_id: str, checksum: str):
        """
        TODO
        :param configuration_id:
        :param checksum:
        :return:
        """


class MemoryStorage(Storage):
    """
    TODO
    """
    def __init__(self):
        self._data: Dict[str, str] = {}

    def get_checksum(self, configuration_id: str) -> Optional[str]:
        return self._data.get(configuration_id, None)

    def set_checksum(self, configuration_id: str, checksum: str):
        self._data[configuration_id] = checksum


class DiskStorage(Storage):
    """
    TODO

    This storage was created to quickly get persistence - concurrent access is unsafe!
    """
    def __init__(self, storage_file_location: str):
        self.storage_file_location = storage_file_location

    def get_checksum(self, configuration_id: str) -> Optional[str]:
        if not os.path.exists(self.storage_file_location):
            return None

        with open(self.storage_file_location, "r") as file:
            return json.load(file).get(configuration_id, None)

    def set_checksum(self, configuration_id: str, checksum: str):
        configuration = None
        if not os.path.exists(self.storage_file_location):
            configuration = {}

        with open(self.storage_file_location, "a+") as file:
            file.seek(0)
            if configuration is None:
                configuration = json.load(file)
                file.seek(0)
            file.truncate()
            configuration[configuration_id] = checksum
            file.write(json.dumps(configuration))

