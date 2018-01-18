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
from thriftybuilder.cli.main import main, CHECKSUM_SOURCE_LOCAL_PATH_LONG_PARAMETER
from thriftybuilder.models import BuildConfigurationContainer, DockerBuildConfiguration
from thriftybuilder.storage import MemoryChecksumStorage
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

        self.pre_built_configuration = list(self.configurations)[0]
        builder = DockerBuilder(self.configurations)
        build_result = builder.build(self.pre_built_configuration)
        assert len(build_result) == 1
        self.checksum_storage = MemoryChecksumStorage({
            self.pre_built_configuration.identifier:
                builder.checksum_calculator.calculate_checksum(self.pre_built_configuration)})

    def tearDown(self):
        super().tearDown()
        for location in self._file_configuration_locations:
            os.remove(location)

    def test_build_when_no_checksums(self):
        result = self._captured_main([self.file_configuration_location])
        expected = {configuration.identifier for configuration in self.configurations}
        self.assertEqual(json.loads(result.stdout).keys(), expected)

    def test_build_when_stdin_checksums(self):
        checksums_as_json = json.dumps(self.checksum_storage.get_all_checksums())
        result = self._captured_main([self.file_configuration_location], checksums_as_json)

        expected = {configuration.identifier for configuration in self.configurations
                    if configuration != self.pre_built_configuration}
        self.assertEqual(json.loads(result.stdout).keys(), expected)

    def test_build_when_local_path_checksums(self):
        with NamedTemporaryFile(mode="w") as temp_file:
            json.dump(self.checksum_storage.get_all_checksums(), temp_file.file)
            temp_file.file.flush()
            result = self._captured_main([
                f"--{CHECKSUM_SOURCE_LOCAL_PATH_LONG_PARAMETER}", temp_file.name, self.file_configuration_location])

            expected = {configuration.identifier for configuration in self.configurations
                        if configuration != self.pre_built_configuration}
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
