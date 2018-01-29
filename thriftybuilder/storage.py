import json
import os
from abc import ABCMeta, abstractmethod
from copy import copy
from typing import Optional, Dict, Mapping, Type
from urllib.parse import urlparse

from consullock.managers import ConsulLockManager

from thriftybuilder.common import MissingOptionalDependencyError


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
        Sets all of the checksums from the given id-checksum mappings.
        :param configuration_checksum_mappings: id-checksum mappings
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
    """
    CONSUL_HTTP_TOKEN_ENVIRONMENT_VARIABLE = "CONSUL_HTTP_TOKEN"
    CONSUL_SESSION_LOCK_DEFAULT_TIMEOUT = 120
    TEXT_ENCODING = "utf-8"

    @staticmethod
    def _load_consul_class() -> Type:
        """
        Loads the Consul class at run time (optional requirement).
        :return: the Consul class
        :raises MissingOptionalDependencyError: if a required dependency is not installed
        """
        try:
            from consul import Consul
        except ImportError as e:
            raise MissingOptionalDependencyError(
                "You must install `python-consul` separately to use this type of storage") from e
        return Consul

    @property
    def url(self) -> str:
        return self._consul_client.http.base_uri
    
    @property
    def token(self) -> str:
        return self._consul_client.token

    def __init__(self, data_key: str, lock_key: str, url: str=None, token: str=None, consul_client=None,
                 configuration_checksum_mappings: Mapping[str, str] = None):
        Consul = ConsulChecksumStorage._load_consul_class()

        if url is not None and consul_client is not None:
            raise ValueError("Cannot use both `url` and `consul_client`")

        self.data_key = data_key
        self.lock_key = lock_key

        consul_client_kwargs: Dict = {}
        if url is not None:
            parsed_url = urlparse(url)
            consul_client_kwargs["host"] = parsed_url.hostname
            consul_client_kwargs["port"] = parsed_url.port
            consul_client_kwargs["scheme"] = parsed_url.scheme if len(parsed_url.scheme) > 0 else "http"
        self._consul_client = consul_client if consul_client is not None else Consul(**consul_client_kwargs)

        if token is None:
            token = os.environ.get(ConsulChecksumStorage.CONSUL_HTTP_TOKEN_ENVIRONMENT_VARIABLE, None)
        if token is not None:
            # Work around for https://github.com/cablehead/python-consul/issues/170
            self._consul_client.token = token
            self._consul_client.http.session.headers.update({"X-Consul-Token": token})

        self._lock_manager = ConsulLockManager(
            consul_client=self._consul_client,
            session_ttl_in_seconds=ConsulChecksumStorage.CONSUL_SESSION_LOCK_DEFAULT_TIMEOUT)

        super().__init__(configuration_checksum_mappings)

    def get_checksum(self, configuration_id: str) -> Optional[str]:
        return self.get_all_checksums().get(configuration_id)

    def get_all_checksums(self) -> Dict[str, str]:
        value = self._consul_client.kv.get(self.data_key)[1]
        if value is None:
            return {}
        value = value["Value"].decode(ConsulChecksumStorage.TEXT_ENCODING)
        return json.loads(value)

    def set_checksum(self, configuration_id: str, checksum: str):
        with self._lock_manager.acquire(self.lock_key):
            value = self.get_all_checksums()
            value[configuration_id] = checksum
            self._consul_client.kv.put(self.data_key, json.dumps(value, sort_keys=True))

    def set_all_checksums(self, configuration_checksum_mappings: Mapping[str, str]):
        with self._lock_manager.acquire(self.lock_key):
            value = self.get_all_checksums()
            value.update(configuration_checksum_mappings)
            self._consul_client.kv.put(self.data_key, json.dumps(value, sort_keys=True))
