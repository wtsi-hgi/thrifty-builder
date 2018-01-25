from json import JSONEncoder, JSONDecoder
from typing import Iterable, Dict

import os
import yaml
from hgijson import JsonPropertyMapping, MappingJSONEncoderClassBuilder, MappingJSONDecoderClassBuilder
from jinja2 import Template

from thriftybuilder.build_configurations import DockerBuildConfiguration
from thriftybuilder.containers import BuildConfigurationContainer
from thriftybuilder.storage import ChecksumStorage, DiskChecksumStorage, ConsulChecksumStorage, MemoryChecksumStorage

DOCKER_PROPERTY = "docker"

DOCKER_IMAGES_PROPERTY = "images"
DOCKER_IMAGE_NAME_PROPERTY = "name"
DOCKER_IMAGE_DOCKERFILE_PROPERTY = "dockerfile"
DOCKER_IMAGE_CONTEXT_PROPERTY = "context"

DOCKER_REGISTRIES_PROPERTY = "registries"
DOCKER_REGISTRY_URL = "url"
DOCKER_REGISTRY_USERNAME = "username"
DOCKER_REGISTRY_PASSWORD = "password"

CHECKSUM_STORAGE_PROPERTY = "checksum_storage"
CHECKSUM_STORAGE_TYPE_PROPERTY = "type"
CHECKSUM_STORAGE_TYPE_VALUE_MAP = {
    DiskChecksumStorage: "local",
    ConsulChecksumStorage: "consul",
    MemoryChecksumStorage: "stdio"
}
CHECKSUM_STORAGE_TYPE_LOCAL_PATH_PROPERTY = "path"
CHECKSUM_STORAGE_TYPE_CONSUL_DATA_KEY_PROPERTY = "key"
CHECKSUM_STORAGE_TYPE_CONSUL_LOCK_KEY_PROPERTY = "lock"
CHECKSUM_STORAGE_TYPE_CONSUL_URL_PROPERTY = "url"
CHECKSUM_STORAGE_TYPE_CONSUL_TOKEN_PROPERTY = "token"


class DockerRegistry:
    """
    Docker registry.
    """
    def __init__(self, url: str, username: str=None, password: str=None):
        self.url = url
        self.username = username
        self.password = password


class Configuration:
    """
    Build configuration.
    """
    def __init__(self, docker_build_configurations: BuildConfigurationContainer[DockerBuildConfiguration]=None,
                 docker_registries: Iterable[DockerRegistry]=(), checksum_storage: ChecksumStorage=None):
        self.docker_build_configurations = docker_build_configurations if docker_build_configurations is not None \
            else BuildConfigurationContainer[DockerBuildConfiguration]()
        self.docker_registries = list(docker_registries)
        self.checksum_storage = checksum_storage if checksum_storage is not None else MemoryChecksumStorage()


def read_configuration(location: str) -> Configuration:
    """
    Reads the configuration file in the given location.
    :param location: location of the configuration file
    :return: parsed configuration from file
    """
    location = _process_path(location)

    with open(location, "r") as file:
        file_context = file.read()
        rendered_file_contents = Template(file_context).render(env=os.environ)
        raw_configuration = yaml.load(rendered_file_contents)

    # Pre-process to convert relative paths to absolute
    paths_relative_to = os.path.abspath(os.path.dirname(location))

    if CHECKSUM_STORAGE_TYPE_LOCAL_PATH_PROPERTY in raw_configuration.get(CHECKSUM_STORAGE_PROPERTY, {}):
        path = raw_configuration[CHECKSUM_STORAGE_PROPERTY][CHECKSUM_STORAGE_TYPE_LOCAL_PATH_PROPERTY]
        raw_configuration[CHECKSUM_STORAGE_PROPERTY][CHECKSUM_STORAGE_TYPE_LOCAL_PATH_PROPERTY] = _process_path(
            path, paths_relative_to)

    raw_docker_images = raw_configuration.get(DOCKER_PROPERTY, {}).get(DOCKER_IMAGES_PROPERTY, [])
    for raw_docker_image in raw_docker_images:
        raw_docker_image[DOCKER_IMAGE_DOCKERFILE_PROPERTY] = _process_path(
            raw_docker_image[DOCKER_IMAGE_DOCKERFILE_PROPERTY], paths_relative_to)
        if DOCKER_IMAGE_CONTEXT_PROPERTY in raw_docker_image:
            raw_docker_image[DOCKER_IMAGE_CONTEXT_PROPERTY] = _process_path(
                raw_docker_image[DOCKER_IMAGE_CONTEXT_PROPERTY], paths_relative_to)

    return ConfigurationJSONDecoder().decode_parsed(raw_configuration)


def _process_path(path: str, path_relative_to: str=os.getcwd()) -> str:
    """
    Processes the given path.
    :param path: path to process
    :param path_relative_to: path to make given path relative to if it is relative
    :return: absolute path
    """
    path = os.path.expanduser(path)
    return os.path.join(path_relative_to, path) if not os.path.isabs(path) else path


_disk_checksum_storage_mappings = [
    JsonPropertyMapping(CHECKSUM_STORAGE_TYPE_LOCAL_PATH_PROPERTY, "storage_file_location", "storage_file_location")
]
DiskChecksumStorageJSONEncoder = MappingJSONEncoderClassBuilder(
    DiskChecksumStorage, _disk_checksum_storage_mappings).build()
DiskChecksumStorageJSONDecoder = MappingJSONDecoderClassBuilder(
    DiskChecksumStorage, _disk_checksum_storage_mappings).build()

_consul_checksum_storage_mappings = [
    JsonPropertyMapping(CHECKSUM_STORAGE_TYPE_CONSUL_DATA_KEY_PROPERTY, "data_key", "data_key"),
    JsonPropertyMapping(CHECKSUM_STORAGE_TYPE_CONSUL_LOCK_KEY_PROPERTY, "lock_key", "lock_key", optional=True),
    JsonPropertyMapping(CHECKSUM_STORAGE_TYPE_CONSUL_URL_PROPERTY, "url", "url", optional=True),
    JsonPropertyMapping(CHECKSUM_STORAGE_TYPE_CONSUL_TOKEN_PROPERTY, "token", "token", optional=True)
]
ConsulChecksumStorageJSONEncoder = MappingJSONEncoderClassBuilder(
    ConsulChecksumStorage, _consul_checksum_storage_mappings).build()
ConsulChecksumStorageJSONDecoder = MappingJSONDecoderClassBuilder(
    ConsulChecksumStorage, _consul_checksum_storage_mappings).build()


class ChecksumStorageJSONDecoder(JSONDecoder):
    def decode(self, obj_as_json, **kwargs):
        parsed_json = super().decode(obj_as_json)
        if parsed_json[CHECKSUM_STORAGE_TYPE_PROPERTY] == CHECKSUM_STORAGE_TYPE_VALUE_MAP[MemoryChecksumStorage]:
            return MemoryChecksumStorage()
        return {
            CHECKSUM_STORAGE_TYPE_VALUE_MAP[DiskChecksumStorage]: DiskChecksumStorageJSONDecoder(),
            CHECKSUM_STORAGE_TYPE_VALUE_MAP[ConsulChecksumStorage]: ConsulChecksumStorageJSONDecoder()
        }[parsed_json[CHECKSUM_STORAGE_TYPE_PROPERTY]].decode(obj_as_json)


class ChecksumStorageJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, MemoryChecksumStorage):
            encoded = {}
        else:
            encoded = {
                DiskChecksumStorage: DiskChecksumStorageJSONEncoder(),
                ConsulChecksumStorage: ConsulChecksumStorageJSONEncoder()
            }[type(obj)].default(obj)
        encoded.update({
            CHECKSUM_STORAGE_TYPE_PROPERTY: CHECKSUM_STORAGE_TYPE_VALUE_MAP[type(obj)]
        })
        return encoded


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


_docker_registry_mappings = [
    JsonPropertyMapping(DOCKER_REGISTRY_URL, "url", "url"),
    JsonPropertyMapping(DOCKER_REGISTRY_USERNAME, "username", optional=True),
    JsonPropertyMapping(DOCKER_REGISTRY_PASSWORD, "password", optional=True)
]
DockerRegistryJSONEncoder = MappingJSONEncoderClassBuilder(DockerRegistry, _docker_registry_mappings).build()
DockerRegistryJSONDecoder = MappingJSONDecoderClassBuilder(DockerRegistry, _docker_registry_mappings).build()


_configuration_mappings = [
    JsonPropertyMapping(
        DOCKER_IMAGES_PROPERTY, "docker_build_configurations", "docker_build_configurations",
        collection_factory=BuildConfigurationContainer, parent_json_properties=[DOCKER_PROPERTY],
        encoder_cls=DockerBuildConfigurationJSONEncoder, decoder_cls=DockerBuildConfigurationJSONDecoder),
    JsonPropertyMapping(
        DOCKER_REGISTRIES_PROPERTY, "docker_registries", "docker_registries", parent_json_properties=[DOCKER_PROPERTY],
        encoder_cls=DockerRegistryJSONEncoder, decoder_cls=DockerRegistryJSONDecoder, optional=True),
    JsonPropertyMapping(
        CHECKSUM_STORAGE_PROPERTY, "checksum_storage", "checksum_storage", encoder_cls=ChecksumStorageJSONEncoder,
        decoder_cls=ChecksumStorageJSONDecoder, optional=True)
]
ConfigurationJSONEncoder = MappingJSONEncoderClassBuilder(Configuration, _configuration_mappings).build()
ConfigurationJSONDecoder = MappingJSONDecoderClassBuilder(Configuration, _configuration_mappings).build()
