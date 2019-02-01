import os
from abc import ABCMeta
from typing import Generic, Callable, Iterable

from thriftybuilder.build_configurations import DockerBuildConfiguration, BuildConfigurationType, \
    BuildConfigurationManager
from thriftybuilder.common import DEFAULT_ENCODING
from thriftybuilder.hashers import Hasher, Md5Hasher


class ChecksumCalculator(Generic[BuildConfigurationType], BuildConfigurationManager[BuildConfigurationType],
                         metaclass=ABCMeta):
    """
    Build configuration checksum calculator.
    """
    def __init__(self, managed_build_configurations: Iterable[BuildConfigurationType]=None,
                 hasher_generator: Callable[[], Hasher]=lambda: Md5Hasher()):
        """
        Constructor.
        :param managed_build_configurations: see `BuildConfigurationManager.__init__`
        :param hasher_generator: hash generator
        """
        super().__init__(managed_build_configurations)
        self.hasher_generator = hasher_generator

    def calculate_checksum(self, build_configuration: BuildConfigurationType) -> str:
        """
        Calculates a checksum for the given build configuration.
        :return: the checksum associated to the configuration
        """
        used_files_checksum = self.calculate_used_files_checksum(build_configuration)
        dependency_checksum = self.calculate_dependency_checksum(build_configuration)
        return self.hasher_generator().update(used_files_checksum).update(dependency_checksum).generate()

    def calculate_used_files_checksum(self, build_configuration: BuildConfigurationType) -> str:
        """
        Calculates the checksum associated to the files that the build configuration uses.
        :param build_configuration: the build configuration to consider
        :return: the calculated checksum
        """
        hasher = self.hasher_generator()
        for file_path in sorted(build_configuration.used_files):
            if not os.path.isdir(file_path):
                with open(file_path, "rb") as file:
                    hasher.update(file.read())
            hasher.update(os.path.relpath(file_path, build_configuration.context))
            hasher.update(str(os.stat(file_path).st_mode & 0o777))
        return hasher.generate()

    def calculate_dependency_checksum(self, build_configuration: BuildConfigurationType) -> str:
        """
        Calculates the checksum associated to the dependencies of the given build configuration.
        :param build_configuration: the build configuration to consider
        :return: the calculated checksum
        """
        parent_build_configuration = self.managed_build_configurations.get(build_configuration.from_image)
        return self.calculate_checksum(parent_build_configuration) if parent_build_configuration is not None else ""


class DockerChecksumCalculator(ChecksumCalculator[DockerBuildConfiguration]):
    """
    Docker build checksum calculator.
    """
    def calculate_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        general_checksum = super().calculate_checksum(build_configuration)
        configuration_checksum = self.calculate_configuration_checksum(build_configuration)
        return self.hasher_generator().update(configuration_checksum).update(general_checksum).generate()

    def calculate_configuration_checksum(self, build_configuration: DockerBuildConfiguration) -> str:
        """
        Calculates the checksum associated to the given build configuration Dockerfile.
        :param build_configuration: the build configuration to consider
        :return: the calculated checksum
        """
        hasher = self.hasher_generator()
        for command in build_configuration.commands:
            hasher.update(command)
        return hasher.generate()
