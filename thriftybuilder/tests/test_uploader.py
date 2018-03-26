import unittest
from abc import ABCMeta, abstractmethod
from typing import Generic, Dict

from thriftybuilder.builders import DockerBuilder
from thriftybuilder.checksums import ChecksumCalculator, DockerChecksumCalculator
from thriftybuilder.build_configurations import BuildConfigurationType, DockerBuildConfiguration
from thriftybuilder.configuration import DockerRegistry
from thriftybuilder.storage import MemoryChecksumStorage
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration, TestWithDockerRegistry
from thriftybuilder.tests._examples import name_generator
from thriftybuilder.uploader import DockerUploader, BuildArtifactUploader


class _TestBuildArtifactUploader(Generic[BuildConfigurationType], unittest.TestCase,
                                 metaclass=ABCMeta):
    """
    Tests for `BuildArtifactUploader`.
    """
    @property
    @abstractmethod
    def checksum_calculator(self) -> ChecksumCalculator[BuildConfigurationType]:
        """
        Gets checksum calculator for the build configuration type used in tests.
        :return: checksum calculator
        """

    @abstractmethod
    def create_uploader(self) -> BuildArtifactUploader[BuildConfigurationType]:
        """
        Creates uploader to test.
        :return: uploader
        """

    @abstractmethod
    def create_built_configuration(self, configuration_args: Dict=None) -> BuildConfigurationType:
        """
        Creates a built configuration to upload.
        :param configuration_args: arguments to use when creating the build configuration
        :return: configuration that has had build artifacts.
        """

    @abstractmethod
    def is_uploaded(self, configuration: BuildConfigurationType) -> bool:
        """
        Checks whether the given configuration has been uploaded.
        :param configuration: the configuration
        :return: whether the configuration has been uploaded
        """

    def setUp(self):
        super().setUp()
        self.checksum_storage = MemoryChecksumStorage()
        self.configuration = self.create_built_configuration()
        self.uploader = self.create_uploader()

    def test_upload(self):
        assert not self.is_uploaded(self.configuration)
        self.uploader.upload(self.configuration)
        checksum = self.checksum_calculator.calculate_checksum(self.configuration)
        self.assertEqual(checksum, self.checksum_storage.get_checksum(self.configuration.identifier))
        self.assertTrue(self.is_uploaded(self.configuration))


class TestDockerUploader(_TestBuildArtifactUploader[DockerBuildConfiguration], TestWithDockerBuildConfiguration,
                         TestWithDockerRegistry):
    """
    Tests for `DockerUploader`.
    """
    @property
    def checksum_calculator(self) -> DockerChecksumCalculator:
        return DockerChecksumCalculator()

    def create_uploader(self) -> DockerUploader:
        return DockerUploader(self.checksum_storage, DockerRegistry(self.registry_location), self.checksum_calculator)

    def create_built_configuration(self, configuration_args: Dict=None) -> DockerBuildConfiguration:
        if configuration_args is None:
            configuration_args = {}
        _, configuration = self.create_docker_setup(**configuration_args)
        build_result = DockerBuilder((configuration,), checksum_calculator=self.checksum_calculator) \
            .build(configuration)
        assert len(build_result) == 1
        return configuration

    def is_uploaded(self, configuration: DockerBuildConfiguration) -> bool:
        return TestWithDockerRegistry.is_uploaded(self, configuration)

    def test_upload_tagged(self):
        configuration = self.create_built_configuration(dict(image_name=f"{name_generator()}:version"))
        assert not self.is_uploaded(configuration)
        self.uploader.upload(configuration)
        checksum = self.checksum_calculator.calculate_checksum(configuration)
        self.assertEqual(checksum, self.checksum_storage.get_checksum(configuration.identifier))
        self.assertTrue(self.is_uploaded(configuration))



del _TestBuildArtifactUploader

if __name__ == "__main__":
    unittest.main()
