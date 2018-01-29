import os
from abc import ABCMeta, abstractmethod
from typing import Generic, Callable

from checksumdir import dirhash

from thriftybuilder.common import DEFAULT_ENCODING
from thriftybuilder.hashers import Hasher, Md5Hasher
from thriftybuilder.build_configurations import DockerBuildConfiguration, BuildConfigurationType, \
    BuildConfigurationManager


class ChecksumCalculator(Generic[BuildConfigurationType], metaclass=ABCMeta):
    """
    Build configuration checksum calculator.
    """
    @abstractmethod
    def calculate_checksum(self, build_configuration: BuildConfigurationType) -> str:
        """
        Calculates a checksum for the given build configuration.
        :return: the checksum associated to the configuration
        """

    def __init__(self, hasher_generator: Callable[[], Hasher]=lambda: Md5Hasher(), *args, **kwargs):
        """
        Constructor.
        :param hasher_generator: hash generator
        """
        super().__init__(*args, **kwargs)
        self.hasher_generator = hasher_generator

    def calculate_used_files_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        Calculates the checksum associated to the files that the build configuration uses.
        :param build_configuration: the build configuration to consider
        :return: the calculated checksum
        """
        hasher = self.hasher_generator()
        for file_path in sorted(build_configuration.used_files):
            if os.path.isdir(file_path):
                hasher.update(dirhash(file_path).encode(DEFAULT_ENCODING))
            else:
                with open(file_path, "rb") as file:
                    hasher.update(file.read())
        return hasher.generate()


class DockerChecksumCalculator(
        ChecksumCalculator[DockerBuildConfiguration], BuildConfigurationManager[DockerBuildConfiguration]):
    """
    Docker build checksum calculator.
    """
    def calculate_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        Note: does not consider file metadata when calculating checksum.
        """
        configuration_checksum = self.calculate_configuration_checksum(build_configuration)
        used_files_checksum = self.calculate_used_files_checksum(build_configuration)
        dependency_checksum = self.calculate_dependency_checksum(build_configuration)
        return self.hasher_generator().update(configuration_checksum).update(used_files_checksum) \
            .update(dependency_checksum).generate()

    def calculate_configuration_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        Calculates the checksum associated to the given build configuration Dockerfile.
        :param build_configuration: the build configuration to consider
        :return: the calculated checksum
        """
        hasher = self.hasher_generator()
        for command in build_configuration.commands:
            hasher.update(command.original.encode(DEFAULT_ENCODING))
        return hasher.generate()

    # TODO: Should probably go into superclass
    def calculate_dependency_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        Calculates the checksum associated to the dependencies of the given build configuration.
        :param build_configuration: the build configuration to consider
        :return: the calculated checksum
        """
        parent_build_configuration = self.managed_build_configurations.get(build_configuration.from_image)
        return self.calculate_checksum(parent_build_configuration) if parent_build_configuration is not None else ""
