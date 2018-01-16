import json
import os
import unittest
from tempfile import NamedTemporaryFile
from typing import List

import yaml
from capturewrap import CaptureWrapBuilder

from thriftybuilder.cli.configuration import FileConfiguration, FileConfigurationJSONEncoder
from thriftybuilder.cli.main import main
from thriftybuilder.models import BuildConfigurationContainer, DockerBuildConfiguration
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration


class TestMain(TestWithDockerBuildConfiguration):
    """
    TODO
    """
    def setUp(self):
        super().setUp()
        self._file_configuration_locations: List[str] = []
        self._captured_main = CaptureWrapBuilder(capture_stdout=True, capture_exception=True).build(main)

    def tearDown(self):
        super().tearDown()
        for location in self._file_configuration_locations:
            os.remove(location)

    def test_build_new(self):
        _, configuration_1 = self.create_docker_setup()
        _, configuration_2 = self.create_docker_setup()

        configuration_container = BuildConfigurationContainer[DockerBuildConfiguration](
            managed_build_configurations=[configuration_1, configuration_2])

        file_configuration = FileConfiguration(docker_build_configurations=configuration_container)
        configuration_location = self._file_configuration_to_file(file_configuration)

        result = self._captured_main([configuration_location])
        self.assertEqual(0, result.exception.code)
        self.assertCountEqual(
            json.loads(result.stdout), {configuration.identifier for configuration in configuration_container})

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
