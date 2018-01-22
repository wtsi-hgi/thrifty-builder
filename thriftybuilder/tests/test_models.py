import os
import unittest

from thriftybuilder.meta import PACKAGE_NAME
from thriftybuilder.build_configurations import DockerBuildConfiguration, _ADD_DOCKER_COMMAND, \
    _COPY_DOCKER_COMMAND, DOCKER_IGNORE_FILE
from thriftybuilder.containers import BuildConfigurationContainer
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration, DOCKERFILE_PATH
from thriftybuilder.tests._examples import EXAMPLE_IMAGE_NAME, EXAMPLE_FROM_IMAGE_NAME, EXAMPLE_FILE_NAME_1


class TestBuildConfigurationContainer(TestWithDockerBuildConfiguration):
    """
    Tests for `BuildConfigurationContainer`.
    """
    def setUp(self):
        super().setUp()
        _, self.configuration = self.create_docker_setup()
        self.container = BuildConfigurationContainer[DockerBuildConfiguration]()

    def test_setup_with_items(self):
        configurations = [self.create_docker_setup(image_name=f"{PACKAGE_NAME}-{i}")[1] for i in range(5)]
        container = BuildConfigurationContainer(configurations)
        self.assertCountEqual(configurations, container)

    def test_len(self):
        length = 5
        self.container.add_all([self.create_docker_setup(image_name=f"{PACKAGE_NAME}-{i}")[1] for i in range(length)])
        self.assertEqual(length, len(self.container))

    def test_index_when_not_added(self):
        _, default = self.create_docker_setup()
        try:
            self.container[self.configuration.identifier]
        except KeyError:
            pass

    def test_index(self):
        self.container.add(self.configuration)
        self.assertEqual(self.configuration, self.container[self.configuration.identifier])

    def test_get_when_not_added(self):
        _, default = self.create_docker_setup()
        self.assertEqual(default, self.container.get(self.configuration.identifier, default=default))

    def test_get(self):
        self.container.add(self.configuration)
        self.assertEqual(self.configuration, self.container.get(self.configuration.identifier))

    def test_add_when_not_added(self):
        self.container.add(self.configuration)
        self.assertCountEqual([self.configuration], self.container)

    def test_add_when_added(self):
        _, configuration_2 = self.create_docker_setup(image_name=self.configuration.identifier)
        self.container.add(self.configuration)
        self.container.add(configuration_2)
        self.assertCountEqual([configuration_2], self.container)

    def test_add_all(self):
        configurations = [self.create_docker_setup(image_name=f"{PACKAGE_NAME}-{i}")[1] for i in range(5)]
        self.container.add_all(configurations)
        self.assertCountEqual(configurations, self.container)

    def test_remove_when_not_added(self):
        self.assertRaises(KeyError, self.container.remove, self.configuration)

    def test_remove(self):
        self.container.add(self.configuration)
        assert len(self.container) == 1 and self.container[self.configuration.identifier] == self.configuration
        self.container.remove(self.configuration)
        self.assertEqual(0, len(self.container))


class TestDockerBuildConfiguration(TestWithDockerBuildConfiguration):
    """
    Tests for `DockerBuildConfiguration`.
    """
    def test_identifier(self):
        _, configuration = self.create_docker_setup(image_name=EXAMPLE_IMAGE_NAME)
        self.assertEqual(EXAMPLE_IMAGE_NAME, configuration.identifier)

    def test_requires(self):
        _, configuration = self.create_docker_setup(from_image_name=EXAMPLE_FROM_IMAGE_NAME)
        self.assertCountEqual([EXAMPLE_FROM_IMAGE_NAME], configuration.requires)

    def test_used_files_when_none_added(self):
        _, configuration = self.create_docker_setup()
        self.assertCountEqual([], configuration.used_files)

    def test_used_files_when_one_add(self):
        context_directory, configuration = self.create_docker_setup(
            commands=(f"{_ADD_DOCKER_COMMAND} {EXAMPLE_FILE_NAME_1} /example", ),
            context_files={EXAMPLE_FILE_NAME_1: None})
        used_files = (os.path.relpath(file, start=context_directory) for file in configuration.used_files)
        self.assertCountEqual([EXAMPLE_FILE_NAME_1], used_files)

    def test_used_files_when_add_directory(self):
        directory = "test"
        example_file_paths = [f"{directory}/{suffix}" for suffix in ["a", "b", "c/d/e", "c/d/f"]]
        context_directory, configuration = self.create_docker_setup(
            commands=(f"{_ADD_DOCKER_COMMAND} {directory} /example", ),
            context_files={file_path: None for file_path in example_file_paths})
        used_files = (os.path.relpath(file, start=context_directory) for file in configuration.used_files)
        self.assertCountEqual(example_file_paths, used_files)

    def test_used_files_when_multiple_add(self):
        example_file_paths = ["a", "b", "c/d"]
        context_directory, configuration = self.create_docker_setup(
            commands=[f"{_ADD_DOCKER_COMMAND} {file_path} /{file_path}" for file_path in example_file_paths],
            context_files={file_path: None for file_path in example_file_paths})
        used_files = (os.path.relpath(file, start=context_directory) for file in configuration.used_files)
        self.assertCountEqual(example_file_paths, used_files)

    def test_used_files_when_multiple_add_and_copy(self):
        example_add_file_paths = ("a", "b", "c/d", "e/f/g")

        copy_add_commands = []
        for i in range(len(example_add_file_paths)):
            command = _ADD_DOCKER_COMMAND if i % 2 == 0 else _COPY_DOCKER_COMMAND
            copy_add_commands.append(f"{command} {example_add_file_paths[i]} /{example_add_file_paths[i]}")

        context_directory, configuration = self.create_docker_setup(
            commands=copy_add_commands,
            context_files={file_path: None for file_path in example_add_file_paths})
        used_files = (os.path.relpath(file, start=context_directory) for file in configuration.used_files)
        self.assertCountEqual(example_add_file_paths, used_files)

    def test_from_image_name(self):
        _, configuration = self.create_docker_setup(from_image_name=EXAMPLE_FROM_IMAGE_NAME)
        self.assertEqual(EXAMPLE_FROM_IMAGE_NAME, configuration.from_image)

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
