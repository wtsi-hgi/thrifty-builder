import os
import unittest

from thriftybuilder.configurations import DockerBuildConfiguration, DOCKER_IGNORE_FILE
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration, DOCKERFILE_PATH, \
    FROM_COMMAND
from thriftybuilder.tests._resources.constants import EXAMPLE_IMAGE_NAME
from thriftybuilder.tests._resources.metadata import EXAMPLE_1_DOCKERFILE, EXAMPLE_2_DOCKERFILE, EXAMPLE_3_DOCKERFILE


class TestDockerBuildConfiguration(TestWithDockerBuildConfiguration):
    """
    Tests for `DockerBuildConfiguration`.
    """
    def test_identifier(self):
        _, configuration = self.create_docker_setup(image_name=EXAMPLE_IMAGE_NAME)
        self.assertEqual(EXAMPLE_IMAGE_NAME, configuration.identifier)

    def test_requires(self):
        _, configuration = self.create_docker_setup(image_name=EXAMPLE_IMAGE_NAME)
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
        _, configuration = self.create_docker_setup(commands=[f"{FROM_COMMAND} ubuntu:17.04"])
        self.assertEqual("ubuntu:17.04", configuration.from_image)

    def test_dockerfile_location(self):
        context_location, configuration = self.create_docker_setup()
        self.assertEqual(os.path.join(context_location, DOCKERFILE_PATH), configuration.dockerfile_location)
        
    def test_context(self):
        context_location, configuration = self.create_docker_setup()
        self.assertEqual(context_location, configuration.context)

    def test_get_ignored_files_when_no_ignore_file(self):
        _, configuration = self.create_docker_setup()
        self.assertEqual(0, len(configuration.get_ignored_files()))

    def test_get_ignored_files_when_ignore_file(self):
        ignore_file_patterns = (".abc", "abc", "*.tmp", "all/tmp/*")
        files_to_ignore = (".abc", "abc", "test/abc", "test/test/abc", "test/test/.abc", "test/test/this.tmp",
                           "all/tmp/files")
        other_files = ("test/abc.abc", "other")

        _, configuration = self.create_docker_setup(context_files=dict(
            **{file_name: None for file_name in files_to_ignore},
            **{file_name: None for file_name in other_files},
            **{DOCKER_IGNORE_FILE: "\n".join(ignore_file_patterns)}))

        self.assertCountEqual((f"{configuration.context}/{file_name}" for file_name in files_to_ignore),
                              configuration.get_ignored_files())


if __name__ == "__main__":
    unittest.main()
