import os
import shutil
import unittest
from abc import ABCMeta
from tempfile import mkdtemp

import dockerfile
from typing import List, Dict, Optional, Tuple, Iterable

from thriftybuilder.configurations import DockerBuildConfiguration

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
    TODO
    :param commands:
    :param context_files:
    :param image_name:
    :param from_image_name:
    :return:
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
    TODO
    """
    def setUp(self):
        self.setup_locations: List[str] = []
        self.build_configurations: List[DockerBuildConfiguration] = []

    def tearDown(self):
        for location in self.setup_locations:
            shutil.rmtree(location)

    def create_docker_setup(self, *args, **kwargs) \
            -> Tuple[str, DockerBuildConfiguration]:
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

