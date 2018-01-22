from enum import Enum, auto

import yaml
from hgijson import JsonPropertyMapping, MappingJSONEncoderClassBuilder, MappingJSONDecoderClassBuilder
from wheel.metadata import unique

from thriftybuilder.containers import BuildConfigurationContainer
from thriftybuilder.build_configurations import DockerBuildConfiguration

DOCKER_IMAGES_PROPERTY = "docker_images"
DOCKER_IMAGE_NAME_PROPERTY = "name"
DOCKER_IMAGE_DOCKERFILE_PROPERTY = "dockerfile"
DOCKER_IMAGE_CONTEXT_PROPERTY = "context"


@unique
class ChecksumSource(Enum):
    """
    Checksum storage source.
    """
    STDIN = auto()
    LOCAL = auto()
    CONSUL = auto()


class FileConfiguration:
    """
    Image build configuration from file.
    """
    def __init__(self, docker_build_configurations: BuildConfigurationContainer[DockerBuildConfiguration]):
        self.docker_build_configurations = docker_build_configurations


_docker_build_configuration_mappings = [
    JsonPropertyMapping(DOCKER_IMAGE_NAME_PROPERTY,
                        object_constructor_parameter_name="image_name",
                        object_property_getter=lambda obj: obj.identifier),
    JsonPropertyMapping(DOCKER_IMAGE_DOCKERFILE_PROPERTY, "dockerfile_location", "dockerfile_location"),
    JsonPropertyMapping(DOCKER_IMAGE_CONTEXT_PROPERTY, "context", "context", optional=True)
]
DockerBuildConfigurationJSONEncoder = MappingJSONEncoderClassBuilder(
    DockerBuildConfiguration, _docker_build_configuration_mappings).build()
DockerBuildConfigurationJSONDecoder = MappingJSONDecoderClassBuilder(
    DockerBuildConfiguration, _docker_build_configuration_mappings).build()


_file_configuration_mappings = [
    JsonPropertyMapping(DOCKER_IMAGES_PROPERTY,
                        "docker_build_configurations",
                        "docker_build_configurations",
                        collection_factory=BuildConfigurationContainer,
                        encoder_cls=DockerBuildConfigurationJSONEncoder,
                        decoder_cls=DockerBuildConfigurationJSONDecoder)
]
FileConfigurationJSONEncoder = MappingJSONEncoderClassBuilder(
    FileConfiguration, _file_configuration_mappings).build()
FileConfigurationJSONDecoder = MappingJSONDecoderClassBuilder(
    FileConfiguration, _file_configuration_mappings).build()


def read_file_configuration(location: str) -> FileConfiguration:
    """
    Reads the configuration file in the given location.
    :param location: location of the configuration file
    :return: parsed configuration from file
    """
    with open(location, "r") as file:
        raw_configuration = yaml.load(file)

    return FileConfigurationJSONDecoder().decode_parsed(raw_configuration)
