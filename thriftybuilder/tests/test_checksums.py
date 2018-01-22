import unittest
from typing import Iterable

from thriftybuilder.checksums import DockerChecksumCalculator
from thriftybuilder.build_configurations import DockerBuildConfiguration
from thriftybuilder.containers import BuildConfigurationContainer
from thriftybuilder.tests._common import COPY_DOCKER_COMMAND, ADD_DOCKER_COMMAND, RUN_DOCKER_COMMAND
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration
from thriftybuilder.tests._examples import EXAMPLE_FILE_NAME_1, EXAMPLE_FILE_CONTENTS_1, \
    EXAMPLE_FILE_NAME_2, EXAMPLE_FILE_CONTENTS_2, EXAMPLE_RUN_COMMAND, EXAMPLE_IMAGE_NAME


class TestDockerChecksumCalculator(TestWithDockerBuildConfiguration):
    """
    Tests for `DockerChecksumCalculator`.
    """
    def setUp(self):
        super().setUp()
        self.checksum_calculator = DockerChecksumCalculator()

    def test_calculate_checksum_with_configurations(self):
        configurations = [
            self.create_docker_setup()[1],
            self.create_docker_setup(commands=(EXAMPLE_RUN_COMMAND))[1],
            self.create_docker_setup(commands=(EXAMPLE_RUN_COMMAND, EXAMPLE_RUN_COMMAND))[1],
        ]
        self._assert_different_checksums(configurations)

    def test_calculate_checksum_when_used_files(self):
        add_file_1_command = f"{ADD_DOCKER_COMMAND} {EXAMPLE_FILE_NAME_1} files_1"
        copy_file_2_command = f"{COPY_DOCKER_COMMAND} {EXAMPLE_FILE_NAME_2} files_2"
        configurations = [
            self.create_docker_setup()[1],
            self.create_docker_setup(
                commands=(add_file_1_command, ),
                context_files={EXAMPLE_FILE_NAME_1: EXAMPLE_FILE_CONTENTS_1})[1],
            self.create_docker_setup(
                commands=(copy_file_2_command, ),
                context_files={EXAMPLE_FILE_NAME_2: EXAMPLE_FILE_CONTENTS_2})[1],
            self.create_docker_setup(
                commands=(add_file_1_command, copy_file_2_command),
                context_files={EXAMPLE_FILE_NAME_1: EXAMPLE_FILE_CONTENTS_1,
                               EXAMPLE_FILE_NAME_2: EXAMPLE_FILE_CONTENTS_2})[1],
            self.create_docker_setup(
                commands=(add_file_1_command, copy_file_2_command),
                context_files={EXAMPLE_FILE_NAME_1: EXAMPLE_FILE_CONTENTS_2,
                               EXAMPLE_FILE_NAME_2: EXAMPLE_FILE_CONTENTS_2})[1],
            self.create_docker_setup(
                commands=(add_file_1_command, copy_file_2_command),
                context_files={EXAMPLE_FILE_NAME_1: EXAMPLE_FILE_CONTENTS_1,
                               EXAMPLE_FILE_NAME_2: EXAMPLE_FILE_CONTENTS_1})[1]]
        self._assert_different_checksums(configurations)

    def test_calculate_checksum_with_changing_from_image(self):
        _, from_configuration_1 = self.create_docker_setup(
            image_name=EXAMPLE_IMAGE_NAME)
        _, from_configuration_2 = self.create_docker_setup(
            image_name=EXAMPLE_IMAGE_NAME, commands=(f"{RUN_DOCKER_COMMAND} other", ))

        _, configuration = self.create_docker_setup(from_image_name=EXAMPLE_IMAGE_NAME)

        self.checksum_calculator.managed_build_configurations.add(from_configuration_1)
        checksum_1 = self.checksum_calculator.calculate_checksum(configuration)
        self.checksum_calculator.managed_build_configurations.add(from_configuration_2)
        checksum_2 = self.checksum_calculator.calculate_checksum(configuration)
        self.assertNotEqual(checksum_1, checksum_2)

    def test_calculate_checksum_with_changing_from_from_image(self):
        grandparent_name = "grandparent"
        parent_name = "parent"

        _, grandparent_configuration_1 = self.create_docker_setup(image_name=grandparent_name)
        _, grandparent_configuration_2 = self.create_docker_setup(
            image_name=grandparent_name, commands=(EXAMPLE_RUN_COMMAND, ))
        _, parent_configuration = self.create_docker_setup(image_name=parent_name, from_image_name=grandparent_name)
        _, configuration = self.create_docker_setup(from_image_name=parent_name)

        self.checksum_calculator.managed_build_configurations.add(parent_configuration)
        self.checksum_calculator.managed_build_configurations.add(grandparent_configuration_1)
        checksum_1 = self.checksum_calculator.calculate_checksum(configuration)
        self.checksum_calculator.managed_build_configurations.add(grandparent_configuration_2)
        checksum_2 = self.checksum_calculator.calculate_checksum(configuration)
        self.assertNotEqual(checksum_1, checksum_2)

    def test_calculate_checksum_type(self):
        configuration = self.create_docker_setup()[1]
        calculator = DockerChecksumCalculator(
            managed_build_configurations=BuildConfigurationContainer([configuration]))
        self.assertIsInstance(calculator.calculate_checksum(configuration), str)

    def _assert_different_checksums(self, configurations: Iterable[DockerBuildConfiguration]):
        """
        Assert that the given configurations all have different checksums.
        :param configurations: the configurations to consider
        :raises AssertionError: when the assertion fails
        """
        checksums = set()
        i = 0
        for configuration in configurations:
            checksum = self.checksum_calculator.calculate_checksum(configuration)
            self.assertNotIn(checksum, checksums)
            checksums.add(checksum)
            i += 1
        if len(checksums) != i:
            raise AssertionError()


if __name__ == "__main__":
    unittest.main()
