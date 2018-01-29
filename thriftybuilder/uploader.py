import json
from abc import abstractmethod, ABCMeta
from typing import Generic

import docker

from thriftybuilder._logging import create_logger
from thriftybuilder.checksums import ChecksumCalculator, DockerChecksumCalculator
from thriftybuilder.configuration import DockerRegistry
from thriftybuilder.common import ThriftyBuilderBaseError
from thriftybuilder.build_configurations import BuildConfigurationType, DockerBuildConfiguration
from thriftybuilder.storage import ChecksumStorage

logger = create_logger(__name__)


class UploadError(ThriftyBuilderBaseError):
    """
    Error raised during build artifact upload.
    """


class ImageNotFoundError(UploadError):
    """
    Error raised if image to be uplaoded is not found.
    """
    def __init__(self, name: str, tag: str):
        self.name = name
        self.tag = tag
        super().__init__(f"Error uploading image: name={self.name}, tag={self.tag}")


class BuildArtifactUploader(Generic[BuildConfigurationType], metaclass=ABCMeta):
    """
    Uploader of build artifacts resulting from a build to a remote repository.
    """
    @abstractmethod
    def _upload(self, build_configuration: BuildConfigurationType):
        """
        Uploads the artifacts generated when the given configuration is built.
        :param build_configuration: the configuration that has been built
        """

    def __init__(self, checksum_storage: ChecksumStorage,
                 checksum_calculator: ChecksumCalculator[BuildConfigurationType]):
        """
        Constructor.
        :param checksum_storage: store of build artifact checksums
        :param checksum_calculator: artifact checksum calculator
        """
        self.checksum_storage = checksum_storage
        self.checksum_calculator = checksum_calculator

    def upload(self, build_configuration: BuildConfigurationType):
        """
        Uploads the artifacts generated when the given configuration is built.
        :param build_configuration: the configuration that has been built
        """
        self._upload(build_configuration)
        checksum = self.checksum_calculator.calculate_checksum(build_configuration)
        self.checksum_storage.set_checksum(build_configuration.identifier, checksum)


class DockerUploader(BuildArtifactUploader[DockerBuildConfiguration]):
    """
    Uploader of Docker images resulting from a build to a remote repository.
    """
    DEFAULT_DOCKER_REGISTRY = DockerRegistry("docker.io")
    _TEXT_ENCODING = "utf-8"

    def __init__(self, checksum_storage: ChecksumStorage, docker_registry: DockerRegistry=DEFAULT_DOCKER_REGISTRY,
                 checksum_calculator: ChecksumCalculator[DockerBuildConfiguration]=None):
        checksum_calculator = checksum_calculator if checksum_calculator is not None else DockerChecksumCalculator()
        super().__init__(checksum_storage, checksum_calculator)
        self.docker_registry = docker_registry
        self._docker_client = docker.from_env()

    def _upload(self, build_configuration: DockerBuildConfiguration):
        repository = f"{self.docker_registry.url}/{build_configuration.name}"
        logger.info(f"Uploading {build_configuration.name} (tag={build_configuration.tag}) to "
                    f"{self.docker_registry.url}")
        self._docker_client.api.tag(build_configuration.name, repository, build_configuration.tag)

        auth_config = None
        if self.docker_registry.username is not None and self.docker_registry.password is not None:
            auth_config = {"username": self.docker_registry.username, "password": self.docker_registry.password}

        upload_stream = self._docker_client.images.push(repository, build_configuration.tag, stream=True,
                                                        auth_config=auth_config)
        for line in upload_stream:
            line = line.decode(DockerUploader._TEXT_ENCODING)
            for sub_line in line.split("\r\n"):
                if len(sub_line) > 0:
                    parsed_sub_line = json.loads(sub_line.strip())
                    logger.debug(parsed_sub_line)
                    if "error" in parsed_sub_line:
                        if "image does not exist" in parsed_sub_line["error"]:
                            raise ImageNotFoundError(build_configuration.name, build_configuration.tag)
                        else:
                            raise UploadError(parsed_sub_line["error"])
