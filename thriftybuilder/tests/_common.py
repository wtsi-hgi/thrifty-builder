import dockerfile
import os
import shutil
import unittest
from abc import ABCMeta
from tempfile import mkdtemp
from typing import List, Dict, Optional, Tuple, Iterable

import docker
from docker.errors import ImageNotFound, NullResource

from thriftybuilder.models import DockerBuildConfiguration

DOCKERFILE_PATH = "Dockerfile"
FROM_DOCKER_COMMAND = "FROM"
RUN_DOCKER_COMMAND = "RUN"
ADD_DOCKER_COMMAND = "ADD"
COPY_DOCKER_COMMAND = "COPY"

_RANDOM_NAME = object()

from thriftybuilder.tests._examples import name_generator, EXAMPLE_FROM_IMAGE_NAME


def create_docker_setup(
        commands: Iterable[str]=None, context_files: Dict[str, Optional[str]]=None,
        image_name: str=_RANDOM_NAME, from_image_name: str=EXAMPLE_FROM_IMAGE_NAME) \
        -> Tuple[str, DockerBuildConfiguration]:
    """
    Creates a Docker setup.
    :param commands: commands to put in the Dockerfile. If `None` and `from_image_name` is set, FROM will be set
    :param context_files: dictionary where the key is the name of the context file and the value is its content
    :param image_name: name of the image to setup a build configuration for
    :param from_image_name: the image that the setup one is based off (FROM added to commands if not `None`)
    :return: tuple where the first element is the directory that acts as the context and the second is the associated
    build configuration
    """
    if from_image_name is not None:
        from_command = f"{FROM_DOCKER_COMMAND} {from_image_name}"
        if commands is None:
            commands = (from_command, )
        else:
            commands = (from_command, *commands)
    parsed_commands = dockerfile.parse_string("\n".join(commands))
    if len([command.cmd for command in parsed_commands if command.cmd.lower() == FROM_DOCKER_COMMAND.lower()]) != 1:
        raise ValueError(f"Exactly one \"{FROM_DOCKER_COMMAND}\" command is expected: {commands}")

    context_files = context_files if context_files is not None else {}
    image_name = image_name if image_name != _RANDOM_NAME else f"{name_generator()}:latest"
    temp_directory = mkdtemp()

    dockerfile_location = os.path.join(temp_directory, DOCKERFILE_PATH)
    with open(dockerfile_location, "w") as file:
        for command in commands:
            file.write(f"{command}\n")

    for location, value in context_files.items():
        absolute_location = os.path.join(temp_directory, location)
        os.makedirs(os.path.dirname(absolute_location), exist_ok=True)
        with open(absolute_location, "w") as file:
            if value is None:
                value = ""
            file.write(value)

    return temp_directory, DockerBuildConfiguration(image_name, dockerfile_location)


class TestWithDockerBuildConfiguration(unittest.TestCase, metaclass=ABCMeta):
    """
    Superclass for a test case that uses Docker build configurations.
    """
    def setUp(self):
        self.setup_locations: List[str] = []
        self.build_configurations: List[DockerBuildConfiguration] = []

    def tearDown(self):
        for location in self.setup_locations:
            shutil.rmtree(location)
        docker_client = docker.from_env()
        for configuration in self.build_configurations:
            try:
                docker_client.images.remove(configuration.identifier)
            except (ImageNotFound, NullResource):
                pass

    def create_docker_setup(self, *args, **kwargs) -> Tuple[str, DockerBuildConfiguration]:
        setup_location, build_configuration = create_docker_setup(*args, **kwargs)
        self.setup_locations.append(setup_location)
        self.build_configurations.append(build_configuration)
        return setup_location, build_configuration

    def create_dependent_docker_build_configurations(self, number: int) -> List[DockerBuildConfiguration]:
        configurations = []
        for i in range(number):
            image_name = name_generator(f"{i}-")
            from_image_name = EXAMPLE_FROM_IMAGE_NAME if i == 0 else configurations[i - 1].identifier
            _, configuration = self.create_docker_setup(image_name=image_name, from_image_name=from_image_name)
            configurations.append(configuration)

        return configurations
