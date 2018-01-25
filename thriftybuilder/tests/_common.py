import dockerfile
import os
import shutil
import unittest
from abc import ABCMeta
from tempfile import mkdtemp, NamedTemporaryFile
from typing import List, Dict, Optional, Tuple, Iterable

import docker
import yaml
from consul import Consul
from docker.errors import ImageNotFound, NullResource, NotFound
from useintest.predefined.consul import ConsulServiceController, ConsulDockerisedService
from useintest.services._builders import DockerisedServiceControllerTypeBuilder
from useintest.services.models import DockerisedService

from thriftybuilder.build_configurations import DockerBuildConfiguration
from thriftybuilder.configuration import ConfigurationJSONEncoder, Configuration

DOCKERFILE_PATH = "Dockerfile"
FROM_DOCKER_COMMAND = "FROM"
RUN_DOCKER_COMMAND = "RUN"
ADD_DOCKER_COMMAND = "ADD"
COPY_DOCKER_COMMAND = "COPY"

_RANDOM_NAME = object()

# To avoid a nasty circular dependency, DO NOT move this import up
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
        super().setUp()
        self.docker_client = docker.from_env()
        self._setup_locations: List[str] = []
        self.images_to_delete: List[str] = []

    def tearDown(self):
        super().tearDown()
        for location in self._setup_locations:
            shutil.rmtree(location)
        docker_client = docker.from_env()

        # Nasty OO to avoid multiple-inheritance method invocation ordering problems
        if isinstance(self, TestWithDockerRegistry):
            additional: List[str] = []
            for identifier in self.images_to_delete:
                additional.append(f"{self.registry_location}/{identifier}")
            self.images_to_delete.extend(additional)

        for identifier in self.images_to_delete:
            try:
                docker_client.images.remove(identifier)
            except (ImageNotFound, NullResource):
                pass

    def create_docker_setup(self, *args, **kwargs) -> Tuple[str, DockerBuildConfiguration]:
        setup_location, build_configuration = create_docker_setup(*args, **kwargs)
        self._setup_locations.append(setup_location)
        self.images_to_delete.append(build_configuration.identifier)
        return setup_location, build_configuration

    def create_dependent_docker_build_configurations(self, number: int) -> List[DockerBuildConfiguration]:
        configurations = []
        for i in range(number):
            image_name = name_generator(f"{i}-")
            from_image_name = EXAMPLE_FROM_IMAGE_NAME if i == 0 else configurations[i - 1].identifier
            _, configuration = self.create_docker_setup(image_name=image_name, from_image_name=from_image_name)
            configurations.append(configuration)

        return configurations


class TestWithConsulService(unittest.TestCase, metaclass=ABCMeta):
    """
    Base class for tests that use a Consul service.
    """
    @property
    def consul_service(self) -> ConsulDockerisedService:
        if self._consul_service is None:
            self._consul_service = self._consul_controller.start_service()
        return self._consul_service

    @property
    def consul_client(self) -> Consul:
        if self._consul_client is None:
            self._consul_client = self.consul_service.create_consul_client()
        return self._consul_client

    def setUp(self):
        self._consul_controller = ConsulServiceController()
        self._consul_service = None
        self._consul_client = None
        super().setUp()

    def tearDown(self):
        if self._consul_service is not None:
            self._consul_controller.stop_service(self._consul_service)


class TestWithDockerRegistry(unittest.TestCase, metaclass=ABCMeta):
    """
    Base class for tests that use a (local) Docker registry.
    """
    _RegistryServiceController = DockerisedServiceControllerTypeBuilder(
        repository="registry",
        tag="2",
        name="_RegistryServiceController",
        start_detector=lambda log_line: "listening on" in log_line,
        ports=[5000]).build()

    @property
    def registry_location(self) -> str:
        return f"{self._registry_service.host}:{self._registry_service.port}"

    @property
    def _registry_service(self) -> DockerisedService:
        if self._docker_registry_service is None:
            self._docker_registry_service = self._registry_controller.start_service()
        return self._docker_registry_service

    def setUp(self):
        self._registry_controller = TestWithDockerRegistry._RegistryServiceController()
        self._docker_registry_service = None
        super().setUp()

    def tearDown(self):
        super().tearDown()
        if self._docker_registry_service is not None:
            self._registry_controller.stop_service(self._docker_registry_service)

    def is_uploaded(self, configuration: DockerBuildConfiguration) -> bool:
        docker_client = docker.from_env()
        try:
            docker_client.images.pull(f"{self.registry_location}/{configuration.name}", tag=configuration.tag)
            return True
        except NotFound:
            return False


class TestWithConfiguration(unittest.TestCase, metaclass=ABCMeta):
    """
    Base class for tests that use a configuration.
    """
    def setUp(self):
        super().setUp()
        self._file_configuration_locations: List[str] = []

    def tearDown(self):
        super().tearDown()
        for location in self._file_configuration_locations:
            os.remove(location)

    def configuration_to_file(self, configuration: Configuration) -> str:
        """
        Writes the given configuration to a temp file.
        :param configuration: the configuration to write to file
        :return: location of the written file
        """
        temp_file = NamedTemporaryFile(delete=False)
        self._file_configuration_locations.append(temp_file.name)
        file_configuration_as_json = ConfigurationJSONEncoder().default(configuration)
        with open(temp_file.name, "w") as file:
            yaml.dump(file_configuration_as_json, file, default_style="\"")
        return temp_file.name
