import os
import shutil
import unittest
from abc import ABCMeta
from tempfile import mkdtemp
from typing import List, Dict, Optional, Tuple, Iterable

from thriftybuilder.configurations import DockerBuildConfiguration

DOCKERFILE_PATH = "Dockerfile"
FROM_DOCKER_COMMAND = "FROM"
RUN_DOCKER_COMMAND = "RUN"
ADD_DOCKER_COMMAND = "ADD"
COPY_DOCKER_COMMAND = "COPY"

from thriftybuilder.tests._examples import EXAMPLE_IMAGE_NAME, EXAMPLE_FROM_COMMAND


def create_docker_setup(
        commands: Iterable[str]=(EXAMPLE_FROM_COMMAND, ), context_files: Dict[str, Optional[str]]=None,
        image_name: str=EXAMPLE_IMAGE_NAME) -> Tuple[str, DockerBuildConfiguration]:
    """
    TODO
    :param commands:
    :param context_files:
    :param image_name:
    :return:
    """
    commands = commands if commands is not None else []
    context_files = context_files if context_files is not None else {}
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

    def tearDown(self):
        for location in self.setup_locations:
            shutil.rmtree(location)

    def create_docker_setup(self, *args, **kwargs) \
            -> Tuple[str, DockerBuildConfiguration]:
        setup_location, build_configuration = create_docker_setup(*args, **kwargs)
        self.setup_locations.append(setup_location)
        return setup_location, build_configuration
