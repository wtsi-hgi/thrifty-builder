import unittest

import os

from thriftybuilder.configurations import DockerBuildConfiguration
from thriftybuilder.tests.resources.metadata import EXAMPLE_1_DOCKERFILE, EXAMPLE_2_DOCKERFILE, EXAMPLE_3_DOCKERFILE


class TestDockerBuildConfiguration(unittest.TestCase):
    """
    Tests for `DockerBuildConfiguration`.
    """
    def test_get_dockerfile_location_from_dockerfile(self):
        configuration = DockerBuildConfiguration(dockerfile_location=EXAMPLE_1_DOCKERFILE)
        self.assertEqual(EXAMPLE_1_DOCKERFILE, configuration.dockerfile_location)

    def test_get_dependent_image_from_dockerfile(self):
        configuration = DockerBuildConfiguration(dockerfile_location=EXAMPLE_1_DOCKERFILE)
        self.assertCountEqual(["debian:jessie"], configuration.requires)

    def test_get_used_files_from_dockerfile_when_none_added(self):
        configuration = DockerBuildConfiguration(dockerfile_location=EXAMPLE_1_DOCKERFILE)
        self.assertCountEqual([], configuration.used_files)

    def test_get_used_files_from_dockerfile_when_one_add(self):
        configuration = DockerBuildConfiguration(dockerfile_location=EXAMPLE_2_DOCKERFILE)
        used_files = (os.path.relpath(file, start=os.path.dirname(EXAMPLE_2_DOCKERFILE))
                      for file in configuration.used_files)
        self.assertCountEqual(["used-file", "directory/other-used-file"], used_files)

    def test_get_used_files_from_dockerfile_when_multiple_add(self):
        configuration = DockerBuildConfiguration(dockerfile_location=EXAMPLE_3_DOCKERFILE)
        used_files = (os.path.relpath(file, start=os.path.dirname(EXAMPLE_3_DOCKERFILE))
                      for file in configuration.used_files)
        self.assertCountEqual(["a", "b", "c/d"], used_files)

    def test_get_used_files_from_dockerfile_when_multiple_add_and_copy(self):
        configuration = DockerBuildConfiguration(dockerfile_location=EXAMPLE_3_DOCKERFILE)
        used_files = (os.path.relpath(file, start=os.path.dirname(EXAMPLE_3_DOCKERFILE))
                      for file in configuration.used_files)
        self.assertCountEqual(["a", "b", "c/d"], used_files)

    def _create_docker_build_configuration(self, dockerfile_location: str) -> DockerBuildConfiguration:
        """
        TODO
        :param dockerfile_location:
        :return:
        """
        return DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, dockerfile_location=EXAMPLE_3_DOCKERFILE)




if __name__ == "__main__":
    unittest.main()
