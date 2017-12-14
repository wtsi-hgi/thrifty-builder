import unittest

import os

from thriftybuilder.configurations import DockerBuildConfiguration
from thriftybuilder.tests.resources.constants import EXAMPLE_IMAGE_NAME
from thriftybuilder.tests.resources.metadata import EXAMPLE_1_DOCKERFILE, EXAMPLE_2_DOCKERFILE, EXAMPLE_3_DOCKERFILE


class TestDockerBuildConfiguration(unittest.TestCase):
    """
    Tests for `DockerBuildConfiguration`.
    """
    def test_identifier(self):
        configuration = DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, EXAMPLE_1_DOCKERFILE)
        self.assertEqual(EXAMPLE_IMAGE_NAME, configuration.identifier)

    def test_requires(self):
        configuration = DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, EXAMPLE_1_DOCKERFILE)
        self.assertCountEqual(["debian:jessie"], configuration.requires)

    def test_used_files_when_none_added(self):
        configuration = DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, EXAMPLE_1_DOCKERFILE)
        self.assertCountEqual([], configuration.used_files)

    def test_used_files_when_one_add(self):
        configuration = DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, EXAMPLE_2_DOCKERFILE)
        used_files = (os.path.relpath(file, start=os.path.dirname(EXAMPLE_2_DOCKERFILE))
                      for file in configuration.used_files)
        self.assertCountEqual(["used-file", "directory/other-used-file"], used_files)

    def test_used_files_when_multiple_add(self):
        configuration = DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, EXAMPLE_3_DOCKERFILE)
        used_files = (os.path.relpath(file, start=os.path.dirname(EXAMPLE_3_DOCKERFILE))
                      for file in configuration.used_files)
        self.assertCountEqual(["a", "b", "c/d"], used_files)

    def test_used_files_when_multiple_add_and_copy(self):
        configuration = DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, EXAMPLE_3_DOCKERFILE)
        used_files = (os.path.relpath(file, start=os.path.dirname(EXAMPLE_3_DOCKERFILE))
                      for file in configuration.used_files)
        self.assertCountEqual(["a", "b", "c/d"], used_files)

    def test_from_image(self):
        configuration = DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, EXAMPLE_1_DOCKERFILE)
        self.assertEqual("debian:jessie", configuration.from_image)

    def test_dockerfile_location(self):
        configuration = DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, EXAMPLE_1_DOCKERFILE)
        self.assertEqual(EXAMPLE_1_DOCKERFILE, configuration.dockerfile_location)
        
    def test_context(self):
        configuration = DockerBuildConfiguration(EXAMPLE_IMAGE_NAME, EXAMPLE_1_DOCKERFILE)
        self.assertEqual(os.path.dirname(EXAMPLE_1_DOCKERFILE), configuration.context)


if __name__ == "__main__":
    unittest.main()
