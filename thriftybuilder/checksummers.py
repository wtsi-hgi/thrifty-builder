import hashlib
from abc import ABCMeta, abstractmethod
from typing import Generic, Iterable, Dict

import os
from checksumdir import dirhash

from thriftybuilder.common import DEFAULT_ENCODING
from thriftybuilder.configurations import BuildConfigurationType, DockerBuildConfiguration


class Checksummer(metaclass=ABCMeta, Generic[BuildConfigurationType]):
    """
    TODO
    """
    @abstractmethod
    def calculate_checksum(self, build_configuration: BuildConfigurationType) -> str:
        """
        TODO
        :return:
        """

    def __init__(self, managed_build_configurations: Iterable[BuildConfigurationType]):
        self._managed_build_configurations: Dict[str, BuildConfigurationType] = {}
        for build_configuration in managed_build_configurations:
            self.add_managed(build_configuration)

    def add_managed(self, build_configuration):
        """
        TODO
        :param build_configuration:
        :return:
        """
        self._managed_build_configurations[build_configuration.identifier] = self._managed_build_configurations


class DockerImageChecksummer(Checksummer[DockerBuildConfiguration]):
    """
    TODO
    :param Checksummer:
    :return:
    """
    def calculate_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        Note: does not consider file metadata when calculating checksum.
        """
        configuration_checksum = self.calculate_configuration_checksum(build_configuration)
        used_files_checksum = self.calculate_used_files_checksum(build_configuration)
        from_image_checksum = self.calculate_from_image_checksum(build_configuration)
        return hashlib.md5(configuration_checksum + used_files_checksum + from_image_checksum).hexdigest()

    def calculate_configuration_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        TODO
        :return:
        """
        hash_accumulator = hashlib.md5()
        for command in build_configuration.commands:
            hash_accumulator.update(command.original.encode(DEFAULT_ENCODING))
        return hash_accumulator.hexdigest().encode(DEFAULT_ENCODING)

    def calculate_used_files_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        TODO
        :return:
        """
        hash_accumulator = hashlib.md5()
        for file_path in sorted(build_configuration.used_files):
            if os.path.isdir(file_path):
                hash_accumulator.update(dirhash(file_path).encode(DEFAULT_ENCODING))
            else:
                with open(file_path, "rb") as file:
                    hash_accumulator.update(file.read())
        return hash_accumulator.hexdigest().encode(DEFAULT_ENCODING)

    def calculate_from_image_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        TODO
        :param build_configuration:
        :return:
        """
        # TODO

