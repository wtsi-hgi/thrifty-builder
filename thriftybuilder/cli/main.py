import json
import logging
from argparse import ArgumentParser, Namespace
from enum import Enum, unique
from json import JSONDecodeError
from typing import List, NamedTuple, Dict, Optional

import sys

from thriftybuilder.builders import DockerBuilder
from thriftybuilder.cli.configuration import read_file_configuration
from thriftybuilder.exceptions import ThriftyBuilderBaseError
from thriftybuilder.meta import DESCRIPTION, VERSION, PACKAGE_NAME
from thriftybuilder.storage import MemoryChecksumStorageJSONDecoder

VERBOSE_CLI_SHORT_PARAMETER = "v"
CONFIGURATION_LOCATION_PARAMETER = "configuration-location"
DEFAULT_LOG_VERBOSITY = logging.WARN
CHECKSUM_SOURCE_LONG_PARAMETER = "checksums-from"


@unique
class ChecksumSource(Enum):
    """
    TODO
    """
    STDIN = "stdin"
    # LOCAL = "local"


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
    log_verbosity: int = DEFAULT_LOG_VERBOSITY
    checksum_source: ChecksumSource = ChecksumSource.STDIN


def _create_parser() -> ArgumentParser:
    """
    Creates argument parser for the CLI.
    :return: the argument parser
    """
    parser = ArgumentParser(description=f"{DESCRIPTION} (v{VERSION})")
    parser.add_argument(
        f"-{VERBOSE_CLI_SHORT_PARAMETER}", action="count", default=0,
        help="increase the level of log verbosity (add multiple increase further)")
    parser.add_argument(f"--{CHECKSUM_SOURCE_LONG_PARAMETER}", type=str, default=ChecksumSource.STDIN,
                        choices=[source.value for source in ChecksumSource], help="source of checksums")
    parser.add_argument(CONFIGURATION_LOCATION_PARAMETER, type=str, help="location of configuration")

    return parser


# FIXME: Stole this from `consul-lock`...
def _get_verbosity(parsed_arguments: Dict) -> int:
    """
    Gets the verbosity level from the parsed arguments.
    :param parsed_arguments: the parsed arguments
    :return: the verbosity level implied
    """
    verbosity = DEFAULT_LOG_VERBOSITY - (int(parsed_arguments.get(VERBOSE_CLI_SHORT_PARAMETER)) * 10)
    if verbosity < 10:
        raise InvalidCliArgumentError("Cannot provide any further logging - reduce log verbosity")
    assert verbosity <= logging.CRITICAL
    return verbosity


def parse_cli_configuration(arguments: List[str]) -> CliConfiguration:
    """
    Parses the given CLI arguments.
    :param arguments: the arguments from the CLI
    :return: parsed configuration
    """
    parsed_arguments = {x.replace("_", "-"): y for x, y in vars(_create_parser().parse_args(arguments)).items()}
    checksum_source = parsed_arguments.get(CHECKSUM_SOURCE_LONG_PARAMETER)
    return CliConfiguration(log_verbosity=_get_verbosity(parsed_arguments),
                            checksum_source=ChecksumSource(checksum_source),
                            configuration_location=parsed_arguments[CONFIGURATION_LOCATION_PARAMETER])


def main(cli_arguments: List[str], stdin_content: Optional[str]=None):
    """
    Entrypoint.
    :param cli_arguments: arguments passed in via the CLI
    :param stdin_content: TODO
    :raises SystemExit: always raised
    """
    cli_configuration = parse_cli_configuration(cli_arguments)
    configuration = read_file_configuration(cli_configuration.configuration_location)

    if cli_configuration.log_verbosity:
        logging.getLogger(PACKAGE_NAME).setLevel(cli_configuration.log_verbosity)

    checksum_storage = None
    if cli_configuration.checksum_source == ChecksumSource.STDIN and stdin_content is not None:
        try:
            checksum_storage = json.loads(stdin_content, cls=MemoryChecksumStorageJSONDecoder)
        except JSONDecodeError as e:
            raise UnreadableChecksumStorageError(f"stdin: {stdin_content}") from e

    docker_builder = DockerBuilder(
        managed_build_configurations=configuration.docker_build_configurations, checksum_storage=checksum_storage)
    build_results = docker_builder.build_all()
    print(json.dumps({configuration.identifier: docker_builder.checksum_calculator.calculate_checksum(configuration)
                      for configuration in build_results.keys()}))

    exit(0)


def entrypoint():
    """
    Entry-point to be used by CLI.
    """
    main(sys.argv[1:], None if sys.stdin.isatty() else sys.stdin.read())


if __name__ == "__main__":
    entrypoint()
