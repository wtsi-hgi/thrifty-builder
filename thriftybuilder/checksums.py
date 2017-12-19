import hashlib
import os
from abc import ABCMeta, abstractmethod
from typing import Generic, Optional, Callable, Union

from checksumdir import dirhash

from thriftybuilder.common import DEFAULT_ENCODING, BuildConfigurationManager
from thriftybuilder.configurations import BuildConfigurationType, DockerBuildConfiguration


class Hasher(metaclass=ABCMeta):
    """
    TODO
    """
    @abstractmethod
    def update(self, input: Union[str, bytes]) -> "Hasher":
        """
        TODO
        :param input:
        :return:
        """

    @abstractmethod
    def generate(self) -> str:
        """
        TODO
        :return:
        """

class Md5Hasher(Hasher):
    """
    TODO
    """
    def __init__(self):
        self._md5 = hashlib.md5()

    def update(self, input: Union[str, bytes]) -> "Md5Hasher":
        if isinstance(input, str):
            input = input.encode(DEFAULT_ENCODING)
        self._md5.update(input)
        return self

    def generate(self) -> str:
        return self._md5.hexdigest().encode(DEFAULT_ENCODING)


class ChecksumCalculator(Generic[BuildConfigurationType], metaclass=ABCMeta):
    """
    TODO
    """
    @abstractmethod
    def calculate_checksum(self, build_configuration: BuildConfigurationType) -> str:
        """
        TODO
        :return:
        """

    def __init__(self, hasher_generator: Callable[[], Hasher]=lambda: Md5Hasher()):
        """
        TODO
        :param hasher_generator:
        """
        super().__init__()
        self.hasher_generator = hasher_generator


class DockerImageChecksumCalculator(
        ChecksumCalculator[DockerBuildConfiguration], BuildConfigurationManager[DockerBuildConfiguration]):
    """
    TODO
    """
    def calculate_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        Note: does not consider file metadata when calculating checksum.
        """
        configuration_checksum = self.calculate_configuration_checksum(build_configuration)
        used_files_checksum = self.calculate_used_files_checksum(build_configuration)
        dependency_checksum = self.calculate_dependency_checksum(build_configuration) or b""
        return self.hasher_generator().update(configuration_checksum).update(used_files_checksum) \
            .update(dependency_checksum).generate()

    def calculate_configuration_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        TODO
        :return:
        """
        hasher = self.hasher_generator()
        for command in build_configuration.commands:
            hasher.update(command.original.encode(DEFAULT_ENCODING))
        return hasher.generate()

    def calculate_used_files_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        TODO
        :return:
        """
        hasher = self.hasher_generator()
        for file_path in sorted(build_configuration.used_files):
            if os.path.isdir(file_path):
                hasher.update(dirhash(file_path).encode(DEFAULT_ENCODING))
            else:
                with open(file_path, "rb") as file:
                    hasher.update(file.read())
        return hasher.generate()

    def calculate_dependency_checksum(self, build_configuration: DockerBuildConfiguration) -> Optional[str]:
        """
        TODO
        :param build_configuration:
        :return:
        """
        parent_build_configuration = self.managed_build_configurations.get(build_configuration.from_image)
        return self.calculate_checksum(parent_build_configuration) if parent_build_configuration is not None else None
