from typing import Iterable

from thriftybuilder.checksums import DockerImageChecksumCalculator
from thriftybuilder.configurations import ADD_DOCKER_COMMAND, COPY_DOCKER_COMMAND, DockerBuildConfiguration, \
    FROM_DOCKER_COMMAND
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration
from thriftybuilder.tests._resources.constants import EXAMPLE_FILE_NAME_1, EXAMPLE_FILE_CONTENTS_1, \
    EXAMPLE_FILE_NAME_2, EXAMPLE_FILE_CONTENTS_2, EXAMPLE_FROM_COMMAND, EXAMPLE_RUN_COMMAND, EXAMPLE_IMAGE_NAME


class TestDockerImageChecksumCalculator(TestWithDockerBuildConfiguration):
    """
    Tests for `DockerImageChecksumCalculator`.
    """
    def setUp(self):
        super().setUp()
        self.checksum_calculator = DockerImageChecksumCalculator()

    def test_calculate_checksum_with_configurations(self):
        configurations = (
            self.create_docker_setup(commands=(EXAMPLE_FROM_COMMAND, ))[1],
            self.create_docker_setup(commands=(EXAMPLE_FROM_COMMAND, EXAMPLE_RUN_COMMAND))[1],
            self.create_docker_setup(commands=(EXAMPLE_FROM_COMMAND, EXAMPLE_RUN_COMMAND, EXAMPLE_RUN_COMMAND))[1],
        )
        self._assert_different_checksums(configurations)

    def test_calculate_checksum_when_used_files(self):
        add_file_1_command = f"{ADD_DOCKER_COMMAND} {EXAMPLE_FILE_NAME_1} files_1"
        copy_file_2_command = f"{COPY_DOCKER_COMMAND} {EXAMPLE_FILE_NAME_2} files_2"
        configurations = (
            self.create_docker_setup(
                commands=(EXAMPLE_FROM_COMMAND,))[1],
            self.create_docker_setup(
                commands=(EXAMPLE_FROM_COMMAND, add_file_1_command),
                context_files={EXAMPLE_FILE_NAME_1: EXAMPLE_FILE_CONTENTS_1})[1],
            self.create_docker_setup(
                commands=(EXAMPLE_FROM_COMMAND, copy_file_2_command),
                context_files={EXAMPLE_FILE_NAME_2: EXAMPLE_FILE_CONTENTS_2})[1],
            self.create_docker_setup(
                commands=(EXAMPLE_FROM_COMMAND, add_file_1_command, copy_file_2_command),
                context_files={EXAMPLE_FILE_NAME_1: EXAMPLE_FILE_CONTENTS_1,
                               EXAMPLE_FILE_NAME_2: EXAMPLE_FILE_CONTENTS_2})[1],
            self.create_docker_setup(
                commands=(EXAMPLE_FROM_COMMAND, add_file_1_command, copy_file_2_command),
                context_files={EXAMPLE_FILE_NAME_1: EXAMPLE_FILE_CONTENTS_2,
                               EXAMPLE_FILE_NAME_2: EXAMPLE_FILE_CONTENTS_2})[1],
            self.create_docker_setup(
                commands=(EXAMPLE_FROM_COMMAND, add_file_1_command, copy_file_2_command),
                context_files={EXAMPLE_FILE_NAME_1: EXAMPLE_FILE_CONTENTS_1,
                               EXAMPLE_FILE_NAME_2: EXAMPLE_FILE_CONTENTS_1})[1])
        self._assert_different_checksums(configurations)

    def test_calculate_checksum_with_changing_from_image(self):
        _, from_configuration_1 = self.create_docker_setup(
            image_name=EXAMPLE_IMAGE_NAME)
        _, from_configuration_2 = self.create_docker_setup(
            image_name=EXAMPLE_IMAGE_NAME, commands=(EXAMPLE_FROM_COMMAND, "other"))

        configuration = self.create_docker_setup(commands=(f"{FROM_DOCKER_COMMAND} {EXAMPLE_IMAGE_NAME}", ))[1]

        self.checksum_calculator.managed_build_configurations.add(from_configuration_1)
        checksum_1 = self.checksum_calculator.calculate_checksum(configuration)
        self.checksum_calculator.managed_build_configurations.add(from_configuration_2)
        checksum_2 = self.checksum_calculator.calculate_checksum(configuration)
        self.assertNotEqual(checksum_1, checksum_2)

    def test_calculate_checksum_with_changing_from_from_image(self):
        grandparent_name = "grandparent"
        parent_name = "grandparent"

        _, grandparent_configuration_1 = self.create_docker_setup(
            image_name=grandparent_name)
        _, grandparent_configuration_2 = self.create_docker_setup(
            image_name=grandparent_name, commands=(EXAMPLE_FROM_COMMAND, EXAMPLE_RUN_COMMAND))

        _, parent_configuration = self.create_docker_setup(
            image_name=parent_name, commands=(f"{FROM_DOCKER_COMMAND} {grandparent_name}", ))
        _, configuration = self.create_docker_setup(
            commands=(f"{FROM_DOCKER_COMMAND} {parent_name}", ))

        self.checksum_calculator.managed_build_configurations.add(parent_configuration)
        self.checksum_calculator.managed_build_configurations.add(grandparent_configuration_1)
        checksum_1 = self.checksum_calculator.calculate_checksum(configuration)
        self.checksum_calculator.managed_build_configurations.add(grandparent_configuration_2)
        checksum_2 = self.checksum_calculator.calculate_checksum(configuration)
        self.assertNotEqual(checksum_1, checksum_2)

    def _assert_different_checksums(self, configurations: Iterable[DockerBuildConfiguration]):
        """
        TODO
        :param configurations:
        :return:
        """
        checksums = set()
        i = 0
        for configuration in configurations:
            checksum = self.checksum_calculator.calculate_checksum(configuration)
            self.assertNotIn(checksum, checksums)
            checksums.add(checksum)
            i += 1
        assert len(checksums) == i
