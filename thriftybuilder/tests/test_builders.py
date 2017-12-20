import itertools
import unittest

import docker
from docker.errors import ImageNotFound
from docker.models.images import Image

from thriftybuilder.builders import DockerBuilder
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration


class TestDockerBuilder(TestWithDockerBuildConfiguration):
    """
    Tests for `DockerBuilder`.
    """
    def setUp(self):
        super().setUp()
        self.docker_builder = DockerBuilder()
        self.docker_client = docker.from_env()

    def tearDown(self):
        super().tearDown()
        for build_configuration in self.build_configurations:
            try:
                self.docker_client.images.remove(build_configuration.identifier)
            except ImageNotFound:
                pass

    def test_build_when_from_image_is_not_managed(self):
        _, configuration = self.create_docker_setup()
        assert configuration.identifier not in \
               itertools.chain(*(image.tags for image in self.docker_client.images.list()))
        build_results = self.docker_builder.build(configuration)
        self.assertCountEqual({configuration: configuration.identifier}, build_results)
        self.assertIsInstance(self.docker_client.images.get(configuration.identifier), Image)

    def test_build_when_from_image_is_managed(self):
        configurations = self.create_dependent_docker_build_configurations(4)
        self.docker_builder.managed_build_configurations.add_all(configurations)
        self.docker_builder.managed_build_configurations.add(self.create_docker_setup()[1])

        build_results = self.docker_builder.build(configurations[-1])
        self.assertCountEqual(
            {configuration: configuration.identifier for configuration in configurations}, build_results)

    def test_build_all_when_none_managed(self):
        built = self.docker_builder.build_all()
        self.assertEqual(0, len(built))

    def test_build_all_when_managed(self):
        configurations = self.create_dependent_docker_build_configurations(4)
        self.docker_builder.managed_build_configurations.add_all(configurations)

        build_results = self.docker_builder.build_all()
        self.assertCountEqual(
            {configuration: configuration.identifier for configuration in configurations}, build_results)


if __name__ == "__main__":
    unittest.main()
