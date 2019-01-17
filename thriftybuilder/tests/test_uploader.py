import unittest
from abc import ABCMeta, abstractmethod

from typing import Generic, Dict

from thriftybuilder.build_configurations import BuildConfigurationType, DockerBuildConfiguration
from thriftybuilder.builders import DockerBuilder
from thriftybuilder.checksums import ChecksumCalculator, DockerChecksumCalculator
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

    def assertUploaded(self, configuration: BuildConfigurationType):
        """
        Asserts that the build artifacts associated to the given configuration have been uploaded and checksum data has
        been stored.
        :param configuration: the build configuration that has been uploaded
        :raises AssertionError: if build artifacts have not been uploaded
        """
        checksum = self.checksum_calculator.calculate_checksum(configuration)
        self.assertEqual(checksum, self.checksum_storage.get_checksum(configuration.identifier))
        self.assertTrue(self.is_uploaded(configuration))

    def setUp(self):
        super().setUp()
        self.checksum_storage = MemoryChecksumStorage()
        self.configuration = self.create_built_configuration()
        self.uploader = self.create_uploader()

    def test_upload(self):
        assert not self.is_uploaded(self.configuration)
        self.uploader.upload(self.configuration)
        self.assertUploaded(self.configuration)


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
        build_result = DockerBuilder((configuration,), checksum_calculator_factory=lambda: self.checksum_calculator) \
            .build(configuration)
        assert len(build_result) == 1
        assert not self.is_uploaded(configuration)
        return configuration

    def is_uploaded(self, configuration: DockerBuildConfiguration) -> bool:
        return TestWithDockerRegistry.is_uploaded(self, configuration)

    def test_upload_tagged_legacy(self):
        configuration = self.create_built_configuration(dict(image_name=f"{name_generator()}:version"))
        self.uploader.upload(configuration)
        self.assertUploaded(configuration)
        self.is_uploaded(configuration)

    def test_upload_tagged(self):
        configuration = self.create_built_configuration(dict(image_name=f"{name_generator()}",
                                                             tags=["version"]))
        self.uploader.upload(configuration)
        self.assertUploaded(configuration)
        self.is_uploaded(configuration)

    def test_upload_with_multiple_tags(self):
        configuration = self.create_built_configuration(dict(image_name=f"{name_generator()}",
                                                             tags=["version", "latest"]))
        self.uploader.upload(configuration)
        self.assertUploaded(configuration)
        self.is_uploaded(configuration)

    def test_upload_not_tagged(self):
        configuration = self.create_built_configuration(dict(image_name=name_generator()))
        self.uploader.upload(configuration)
        self.assertUploaded(configuration)


del _TestBuildArtifactUploader

if __name__ == "__main__":
    unittest.main()
