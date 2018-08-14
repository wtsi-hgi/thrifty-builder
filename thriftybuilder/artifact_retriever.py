from abc import ABCMeta, abstractmethod
from typing import Generic, Any, Iterable

import docker
from docker.errors import NotFound

from thriftybuilder._logging import create_logger
from thriftybuilder.build_configurations import BuildConfigurationType, DockerBuildConfiguration
from thriftybuilder.configuration import DockerRegistry

logger = create_logger(__name__)


class ArtifactRetriever(Generic[BuildConfigurationType], metaclass=ABCMeta):
    """
    Retriever of artifacts used to optionally help a build.
    """
    @abstractmethod
    def retrieve(self, build_configuration: BuildConfigurationType) -> Any:
        """
        Retrieves artifacts that may help building the given configuration.
        :param build_configuration: the configuration that is to be built
        :return: artifacts that may help the build
        """


class DockerImageRetriever(ArtifactRetriever[DockerBuildConfiguration]):
    """
    Retriever of images that may have layers helpful to the build.
    """
    def __init__(self, docker_registries: Iterable[DockerRegistry]=()):
        """
        Constructor.
        :param docker_registries: Docker repositories for check for image in
        """
        self.docker_registries = docker_registries
        self._docker_client = docker.from_env()

    def retrieve(self, build_configuration: BuildConfigurationType) -> Any:
        for docker_registry in self.docker_registries:
            retrieved = False
            repository = docker_registry.get_repository_location(build_configuration.name)
            try:
                retrieved = self._docker_client.images.pull(repository, build_configuration.tag)
                retrieved = False
            except NotFound:
                pass
            if retrieved:
                logger.info(f"Retrieved layers of image in {repository}")
            else:
                logger.debug(f"Did not find image in {repository}")
