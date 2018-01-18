import json
import os
import unittest
from tempfile import NamedTemporaryFile
from typing import List

import yaml
from capturewrap import CaptureWrapBuilder

from thriftybuilder.builders import DockerBuilder
from thriftybuilder.checksums import DockerBuildChecksumCalculator
from thriftybuilder.cli.configuration import FileConfiguration, FileConfigurationJSONEncoder
from thriftybuilder.cli.main import main
from thriftybuilder.models import BuildConfigurationContainer, DockerBuildConfiguration
from thriftybuilder.storage import MemoryChecksumStorage, MemoryChecksumStorageJSONEncoder
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration


class TestMain(TestWithDockerBuildConfiguration):
    """
    TODO
    """
    def setUp(self):
        super().setUp()
        self._file_configuration_locations: List[str] = []
        self._captured_main = CaptureWrapBuilder(
            capture_stdout=True, capture_exceptions=lambda e: isinstance(e, SystemExit) and e.code == 0).build(main)

        self.configurations = BuildConfigurationContainer[DockerBuildConfiguration](
            self.create_docker_setup()[1] for _ in range(3))
        self.file_configuration = FileConfiguration(self.configurations)
        self.file_configuration_location = self._file_configuration_to_file(self.file_configuration)

    def tearDown(self):
        super().tearDown()
        for location in self._file_configuration_locations:
            os.remove(location)

    def test_build_when_no_checksums(self):
        result = self._captured_main([self.file_configuration_location])
        expected = {configuration.identifier for configuration in self.configurations}
        self.assertEqual(json.loads(result.stdout).keys(), expected)

    def test_build_when_stdin_checksums(self):
        pre_built_configuration = list(self.configurations)[0]
        pre_build_result = DockerBuilder(self.configurations).build(pre_built_configuration)
        assert len(pre_build_result) == 1
        checksum = DockerBuildChecksumCalculator(
            managed_build_configurations=BuildConfigurationContainer(self.configurations)).\
            calculate_checksum(pre_built_configuration)

        memory_checksum_storage = MemoryChecksumStorage()
        memory_checksum_storage.set_checksum(pre_built_configuration.identifier, checksum)

        stdin_content = json.dumps(memory_checksum_storage, cls=MemoryChecksumStorageJSONEncoder)
        result = self._captured_main([self.file_configuration_location], stdin_content)

        expected = {configuration.identifier for configuration in self.configurations
                    if configuration != pre_built_configuration}
        self.assertEqual(json.loads(result.stdout).keys(), expected)

    def _file_configuration_to_file(self, file_configuration: FileConfiguration) -> str:
        """
        TODO
        :param file_configuration:
        :return:
        """
        temp_file = NamedTemporaryFile(delete=False)
        self._file_configuration_locations.append(temp_file.name)
        with open(temp_file.name, "w") as file:
            yaml.dump(FileConfigurationJSONEncoder().default(file_configuration), file)
        return temp_file.name


if __name__ == "__main__":
    unittest.main()
