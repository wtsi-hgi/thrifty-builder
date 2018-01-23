import json
import os
import unittest
from tempfile import NamedTemporaryFile
from typing import List, Tuple

import yaml
from capturewrap import CaptureWrapBuilder

from thriftybuilder.build_configurations import DockerBuildConfiguration
from thriftybuilder.builders import DockerBuilder
from thriftybuilder.cli import main
from thriftybuilder.configuration import Configuration, ConfigurationJSONEncoder, DockerRegistry
from thriftybuilder.containers import BuildConfigurationContainer
from thriftybuilder.storage import MemoryChecksumStorage, DiskChecksumStorage, ConsulChecksumStorage
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration, TestWithConsulService, TestWithDockerRegistry


class TestMain(TestWithDockerBuildConfiguration, TestWithConsulService, TestWithDockerRegistry):
    """
    Tests for CLI.
    """
    def setUp(self):
        super().setUp()
        self._file_configuration_locations: List[str] = []
        self._captured_main = CaptureWrapBuilder(
            capture_stdout=True, capture_exceptions=lambda e: isinstance(e, SystemExit) and e.code == 0).build(main)

        self.build_configurations = BuildConfigurationContainer[DockerBuildConfiguration](
            self.create_docker_setup()[1] for _ in range(3))
        self.run_configuration = Configuration(self.build_configurations)

        self.pre_built_configuration = list(self.build_configurations)[0]
        builder = DockerBuilder(self.build_configurations)
        build_result = builder.build(self.pre_built_configuration)
        assert len(build_result) == 1
        self.run_configuration.checksum_storage = MemoryChecksumStorage({
            self.pre_built_configuration.identifier:
                builder.checksum_calculator.calculate_checksum(self.pre_built_configuration)})

    def tearDown(self):
        super().tearDown()
        for location in self._file_configuration_locations:
            os.remove(location)

    def test_build_when_no_checksums(self):
        stdout, stderr = self._run(self.run_configuration)
        expected = {configuration.identifier for configuration in self.build_configurations}
        self.assertEqual(json.loads(stdout).keys(), expected)

    def test_build_when_stdin_checksums(self):
        checksums_as_json = json.dumps(self.run_configuration.checksum_storage.get_all_checksums())
        result = self._captured_main([self._file_configuration_to_file(self.run_configuration)], checksums_as_json)

        expected = {configuration.identifier for configuration in self.build_configurations
                    if configuration != self.pre_built_configuration}
        self.assertEqual(json.loads(result.stdout).keys(), expected)

    def test_build_when_local_path_checksums(self):
        with NamedTemporaryFile(mode="w") as temp_file:
            json.dump(self.run_configuration.checksum_storage.get_all_checksums(), temp_file.file)
            temp_file.file.flush()
            self.run_configuration.checksum_storage = DiskChecksumStorage(temp_file.name)
            stdout, stderr = self._run(self.run_configuration)

        expected = {configuration.identifier for configuration in self.build_configurations
                    if configuration != self.pre_built_configuration}
        self.assertEqual(json.loads(stdout).keys(), expected)

    def test_build_when_consul_checksums(self):
        test_key = "example-key"
        checksums_as_json = json.dumps(self.run_configuration.checksum_storage.get_all_checksums())
        self.consul_client.kv.put(test_key, checksums_as_json)
        self.consul_service.setup_environment()
        self.run_configuration.checksum_storage = ConsulChecksumStorage(test_key)

        stdout, stderr = self._run(self.run_configuration)

        expected = {configuration.identifier for configuration in self.build_configurations
                    if configuration != self.pre_built_configuration}
        self.assertEqual(json.loads(stdout).keys(), expected)

    def test_build_then_upload(self):
        docker_registry = DockerRegistry(self.registry_location)
        self.run_configuration.docker_registries.append(docker_registry)
        stdout, stderr = self._run(self.run_configuration)

        parsed_result = json.loads(stdout)
        assert len(parsed_result) == len(self.build_configurations)
        for configuration in self.build_configurations:
            self.assertTrue(self.is_uploaded(configuration))

    def _run(self, file_configuration: Configuration) -> Tuple[str, str]:
        """
        TODO
        :return:
        """
        file_configuration_location = self._file_configuration_to_file(file_configuration)
        result = self._captured_main([file_configuration_location])
        return result.stdout, result.stderr

    def _file_configuration_to_file(self, file_configuration: Configuration) -> str:
        """
        Writes the given file configuration to a temp file.
        :param file_configuration: the file configuration to write to file
        :return: location of the written file
        """
        temp_file = NamedTemporaryFile(delete=False)
        self._file_configuration_locations.append(temp_file.name)
        file_configuration_as_json = ConfigurationJSONEncoder().default(file_configuration)
        with open(temp_file.name, "w") as file:
            yaml.dump(file_configuration_as_json, file)
        return temp_file.name


if __name__ == "__main__":
    unittest.main()
