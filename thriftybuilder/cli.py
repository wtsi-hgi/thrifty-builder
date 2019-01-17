import json
import logging
import sys

import docker
from argparse import ArgumentParser
from docker.errors import APIError
from typing import List, NamedTuple, Dict, Optional

from thriftybuilder._external.verbosity_argument_parser import verbosity_parser_configuration, VERBOSE_PARAMETER_KEY, \
    get_verbosity
from thriftybuilder._logging import create_logger
from thriftybuilder.builders import DockerBuilder
from thriftybuilder.common import ThriftyBuilderBaseError
from thriftybuilder.configuration import read_configuration
from thriftybuilder.meta import DESCRIPTION, VERSION, PACKAGE_NAME, EXECUTABLE_NAME
from thriftybuilder.storage import MemoryChecksumStorage
from thriftybuilder.uploader import DockerUploader

VERBOSITY_SHORT_PARAMETER = verbosity_parser_configuration[VERBOSE_PARAMETER_KEY]
OUTPUT_BUILT_ONLY_LONG_PARAMETER = "built-only"
CONFIGURATION_LOCATION_PARAMETER = "configuration-location"

DEFAULT_LOG_VERBOSITY = logging.WARN
DEFAULT_BUILT_ONLY = False

logger = create_logger(__name__)


class InvalidCliArgumentError(ThriftyBuilderBaseError):
    """
    Raised when an invalid CLI argument has been given.
    """


class UnreadableChecksumStorageError(ThriftyBuilderBaseError):
    """
    Raised when checksum storage is not readable.
    """


class CliConfiguration(NamedTuple):
    """
    CLI configuration.
    """
    configuration_location: str
    output_built_only: bool = DEFAULT_BUILT_ONLY
    log_verbosity: int = DEFAULT_LOG_VERBOSITY


def _create_parser() -> ArgumentParser:
    """
    Creates argument parser for the CLI.
    :return: the argument parser
    """
    parser = ArgumentParser(prog=EXECUTABLE_NAME, description=f"{DESCRIPTION} (v{VERSION})")
    parser.add_argument(f"-{VERBOSITY_SHORT_PARAMETER}", action="count", default=0,
                        help="increase the level of log verbosity (add multiple increase further)")
    parser.add_argument(f"--{OUTPUT_BUILT_ONLY_LONG_PARAMETER}", action="store_true", default=DEFAULT_BUILT_ONLY,
                        help="only print details about newly built images on stdout")
    parser.add_argument(CONFIGURATION_LOCATION_PARAMETER, type=str,
                        help="location of configuration")
    return parser


def parse_cli_configuration(arguments: List[str]) -> CliConfiguration:
    """
    Parses the given CLI arguments.
    :param arguments: the arguments from the CLI
    :return: parsed configuration
    """
    parsed_arguments = {x.replace("_", "-"): y for x, y in vars(_create_parser().parse_args(arguments)).items()}
    return CliConfiguration(log_verbosity=get_verbosity(parsed_arguments),
                            output_built_only=parsed_arguments.get(
                                OUTPUT_BUILT_ONLY_LONG_PARAMETER, DEFAULT_BUILT_ONLY),
                            configuration_location=parsed_arguments[CONFIGURATION_LOCATION_PARAMETER])


def main(cli_arguments: List[str], stdin_content: Optional[str]=None):
    """
    Entrypoint.
    :param cli_arguments: arguments passed in via the CLI
    :param stdin_content: content written on stdin
    :raises SystemExit: always raised
    """
    cli_configuration = parse_cli_configuration(cli_arguments)
    configuration = read_configuration(cli_configuration.configuration_location)

    if cli_configuration.log_verbosity:
        logging.getLogger(PACKAGE_NAME).setLevel(cli_configuration.log_verbosity)

    logger.debug(f"Checksum storage: {configuration.checksum_storage.__class__.__name__}")
    if isinstance(configuration.checksum_storage, MemoryChecksumStorage) and stdin_content:
        logger.info("Reading checksums from stdin")
        configuration.checksum_storage.set_all_checksums(json.loads(stdin_content))

    docker_builder = DockerBuilder(managed_build_configurations=configuration.docker_build_configurations,
                                   checksum_retriever=configuration.checksum_storage)
    build_results = docker_builder.build_all()

    docker_client = docker.from_env()
    try:
        build_configurations_to_upload = list(build_results.keys())
        for build_configuration in configuration.docker_build_configurations:
            if build_configuration.always_upload and build_configuration not in build_configurations_to_upload:
                # build configuration was not just rebuilt but we want to tag it, so pull it from the registries
                # before tagging
                for docker_registry in configuration.docker_registries:
                    repository_location = docker_registry.get_repository_location(build_configuration.name)
                    auth_config = None
                    if docker_registry.username is not None and docker_registry.password is not None:
                        auth_config = {"username": docker_registry.username, "password": docker_registry.password}
                    logger.info(f"Pulling image from {repository_location}")
                    try:
                        docker_client.images.pull(repository_location, auth_config=auth_config)
                    except APIError:
                        logger.info(f"Could not pull from {repository_location}")
                        continue
                    logger.info(f"Pulled {repository_location}, tagging it with local {build_configuration.identifier}")
                    docker_client.api.tag(repository_location, repository=build_configuration.identifier)

                # since always_upload is set, add this build configuration to the list of configs to upload
                build_configurations_to_upload.append(build_configuration)
    finally:
        docker_client.close()

    if len(configuration.docker_registries) == 0:
        logger.info("No Docker registries defined so will not upload images (or update checksums in store)")
    else:
        for repository in configuration.docker_registries:
            with DockerUploader(configuration.checksum_storage, repository) as uploader:
                for build_configuration in build_configurations_to_upload:
                    uploader.upload(build_configuration)

    all_built: Dict[str, str] = {}
    built_now: Dict[str, str] = {}
    for build_configuration in configuration.docker_build_configurations:
        checksum = docker_builder.checksum_calculator.calculate_checksum(build_configuration)
        all_built[build_configuration.identifier] = checksum
        if build_configuration in build_results:
            built_now[build_configuration.identifier] = checksum

    output = built_now
    if not cli_configuration.output_built_only:
        logger.info(f"Build results: %s" % json.dumps(built_now))
        output = all_built
    print(json.dumps(output))

    exit(0)


def entrypoint():
    """
    Entry-point to be used by CLI.
    """
    main(sys.argv[1:], None if sys.stdin.isatty() else sys.stdin.read())


if __name__ == "__main__":
    entrypoint()

