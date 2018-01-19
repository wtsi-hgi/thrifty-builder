import json
import os
from abc import ABCMeta, abstractmethod
from copy import copy

from typing import Optional, Dict, Mapping

from thriftybuilder.exceptions import MissingOptionalDependencyError


class ChecksumStorage(metaclass=ABCMeta):
    """
    Store of mappings between configurations, identified by ID, and checksums.
    """
    @abstractmethod
    def get_checksum(self, configuration_id: str) -> Optional[str]:
        """
        Gets the checksum associated to the given configuration ID.
        :param configuration_id: the ID of the configuration
        :return: the associated checksum or `None` if none stored
        """

    @abstractmethod
    def get_all_checksums(self) -> Dict[str, str]:
        """
        Gets all of the identifer -> checksum mappings.
        :return: all stored mappings
        """

    @abstractmethod
    def set_checksum(self, configuration_id: str, checksum: str):
        """
        Sets the checksum associated to the given configuration ID.
        :param configuration_id: the ID of the configuration
        :param checksum: the checksum associated to the configuration
        """

    def __init__(self, configuration_checksum_mappings: Mapping[str, str]=None):
        if configuration_checksum_mappings is not None:
            self.set_all_checksums(configuration_checksum_mappings)

    def __str__(self) -> str:
        return json.dumps(self.get_all_checksums(), sort_keys=True)

    def __hash__(self) -> hash:
        return hash(str(self))

    def set_all_checksums(self, configuration_checksum_mappings: Mapping[str, str]):
        """
        TODO
        :param configuration_checksum_mappings:
        """
        for configuration_id, checksum in configuration_checksum_mappings.items():
            self.set_checksum(configuration_id, checksum)


class MemoryChecksumStorage(ChecksumStorage):
    """
    In-memory storage for configuration -> checksum mappings.
    """
    def __init__(self, *args, **kwargs):
        self._data: Dict[str, str] = {}
        super().__init__(*args, **kwargs)

    def get_checksum(self, configuration_id: str) -> Optional[str]:
        return self._data.get(configuration_id, None)

    def get_all_checksums(self) -> Dict[str, str]:
        return copy(self._data)

    def set_checksum(self, configuration_id: str, checksum: str):
        self._data[configuration_id] = checksum


class DiskChecksumStorage(ChecksumStorage):
    """
    On-disk storage for configuration -> checksum mappings.

    This storage was created to quickly get persistence - concurrent access is unsafe!
    """
    def __init__(self, storage_file_location: str, *args, **kwargs):
        self.storage_file_location = storage_file_location
        super().__init__(*args, **kwargs)

    def get_checksum(self, configuration_id: str) -> Optional[str]:
        return self.get_all_checksums().get(configuration_id, None)

    def get_all_checksums(self) -> Dict[str, str]:
        if not os.path.exists(self.storage_file_location):
            return {}

        with open(self.storage_file_location, "r") as file:
            return json.load(file)

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


class ConsulChecksumStorage(ChecksumStorage):
    """
    Consul storage for configuration -> checksum mappings.

    Not safe to use on same key in parallel.
    """
    CONSUL_HTTP_TOKEN_ENVIRONMENT_VARIABLE = "CONSUL_HTTP_TOKEN"
    TEXT_ENCODING = "utf-8"

    def __init__(self, data_key: str, consul_client=None, *args, **kwargs):
        try:
            from consul import Consul
        except ImportError as e:
            raise MissingOptionalDependencyError(
                "You must install `python-consul` separately to use this type of storage") from e

        self.data_key = data_key
        self._consul_client = consul_client if consul_client is not None else Consul()

        if ConsulChecksumStorage.CONSUL_HTTP_TOKEN_ENVIRONMENT_VARIABLE in os.environ:
            # Work around for https://github.com/cablehead/python-consul/issues/170
            token = ConsulChecksumStorage.CONSUL_HTTP_TOKEN_ENVIRONMENT_VARIABLE
            self._consul_client.http.session.headers.update({"X-Consul-Token": token})

        super().__init__(*args, **kwargs)

    def get_checksum(self, configuration_id: str) -> Optional[str]:
        return self.get_all_checksums().get(configuration_id)

    def get_all_checksums(self) -> Dict[str, str]:
        value = self._consul_client.kv.get(self.data_key)[1]
        if value is None:
            return {}
        value = value["Value"].decode(ConsulChecksumStorage.TEXT_ENCODING)
        return json.loads(value)

    def set_checksum(self, configuration_id: str, checksum: str):
        value = self.get_all_checksums()
        value[configuration_id] = checksum
        self._consul_client.kv.put(self.data_key, json.dumps(value, sort_keys=True))

    def set_all_checksums(self, configuration_checksum_mappings: Mapping[str, str]):
        value = self.get_all_checksums()
        value.update(configuration_checksum_mappings)
        self._consul_client.kv.put(self.data_key, json.dumps(value, sort_keys=True))
