import json
import os
from abc import ABCMeta, abstractmethod
from copy import copy

from typing import Optional, Dict

from hgijson import JsonPropertyMapping, MappingJSONEncoderClassBuilder, MappingJSONDecoderClassBuilder


class ChecksumStorage(metaclass=ABCMeta):
    """
    Store of mappings between configurations, identified by ID, and checksums.
    """
    @abstractmethod
    def get_all(self) -> Dict[str, str]:
        """
        Gets all of the identifer -> checksum mappings.
        :return: all stored mappings
        """

    @abstractmethod
    def get_checksum(self, configuration_id: str) -> Optional[str]:
        """
        Gets the checksum associated to the given configuration ID.
        :param configuration_id: the ID of the configuration
        :return: the associated checksum or `None` if none stored
        """

    @abstractmethod
    def set_checksum(self, configuration_id: str, checksum: str):
        """
        Sets the checksum associated to the given configuration ID.
        :param configuration_id: the ID of the configuration
        :param checksum: the checksum associated to the configuration
        """

    def __str__(self) -> str:
        return json.dumps(self, cls=ChecksumStorageJSONEncoder, sort_keys=True)

    def __hash__(self) -> hash:
        return hash(str(self))


class MemoryChecksumStorage(ChecksumStorage):
    """
    In-memory storage for configuration -> checksum mappings.
    """
    def __init__(self):
        self._data: Dict[str, str] = {}

    def get_all(self) -> Dict[str, str]:
        return copy(self._data)

    def get_checksum(self, configuration_id: str) -> Optional[str]:
        return self._data.get(configuration_id, None)

    def set_checksum(self, configuration_id: str, checksum: str):
        self._data[configuration_id] = checksum


class DiskChecksumStorage(ChecksumStorage):
    """
    On-disk storage for configuration -> checksum mappings.

    This storage was created to quickly get persistence - concurrent access is unsafe!
    """
    def __init__(self, storage_file_location: str):
        self.storage_file_location = storage_file_location

    def get_all(self) -> Dict[str, str]:
        if not os.path.exists(self.storage_file_location):
            return {}

        with open(self.storage_file_location, "r") as file:
            return json.load(file)

    def get_checksum(self, configuration_id: str) -> Optional[str]:
        return self.get_all().get(configuration_id, None)

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


_storage_configuration_mappings = [
    JsonPropertyMapping(
        "checksums", object_property_getter=lambda obj: obj.get_all(),
        object_property_setter=lambda obj, value: [obj.set_checksum(*x) for x in value.items()] and None)
]
ChecksumStorageJSONEncoder = MappingJSONEncoderClassBuilder(
    ChecksumStorage, _storage_configuration_mappings).build()
ChecksumStorageJSONDecoder = MappingJSONDecoderClassBuilder(
    ChecksumStorage, _storage_configuration_mappings).build()

MemoryChecksumStorageJSONEncoder = MappingJSONEncoderClassBuilder(
    MemoryChecksumStorage, superclasses=(ChecksumStorageJSONEncoder, )).build()
MemoryChecksumStorageJSONDecoder = MappingJSONDecoderClassBuilder(
    MemoryChecksumStorage, superclasses=(ChecksumStorageJSONDecoder, )).build()
