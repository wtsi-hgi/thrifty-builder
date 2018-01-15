import json
import logging
from argparse import ArgumentParser, Namespace
from typing import List, NamedTuple

import sys

from thriftybuilder.builders import DockerBuilder
from thriftybuilder.cli.configuration import read_file_configuration
from thriftybuilder.meta import DESCRIPTION, VERSION, PACKAGE_NAME

VERBOSE_CLI_SHORT_PARAMETER = "v"
DEFAULT_LOG_VERBOSITY = logging.WARN



class InvalidCliArgumentError(Exception):
    """
    Raised when an invalid CLI argument has been given.
    """


class CliConfiguration(NamedTuple):
    """
    CLI configuration.
    """
    configuration_location: str
    log_verbosity: int = DEFAULT_LOG_VERBOSITY


def _create_parser() -> ArgumentParser:
    """
    Creates argument parser for the CLI.
    :return: the argument parser
    """
    parser = ArgumentParser(description=f"{DESCRIPTION} (v{VERSION})")
    parser.add_argument(
        f"-{VERBOSE_CLI_SHORT_PARAMETER}", action="count", default=0,
        help="increase the level of log verbosity (add multiple increase further)")
    parser.add_argument("configuration_location", type=str, help="location of configuration")

    return parser


# FIXME: Stole this from `consul-lock`...
def _get_verbosity(parsed_arguments: Namespace) -> int:
    """
    Gets the verbosity level from the parsed arguments.
    :param parsed_arguments: the parsed arguments
    :return: the verbosity level implied
    """
    verbosity = DEFAULT_LOG_VERBOSITY - (int(vars(parsed_arguments).get(VERBOSE_CLI_SHORT_PARAMETER)) * 10)
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
    parsed_arguments = _create_parser().parse_args(arguments)
    return CliConfiguration(configuration_location=parsed_arguments.configuration_location,
                            log_verbosity=_get_verbosity(parsed_arguments))


def main(cli_arguments: List[str]):
    """
    Entrypoint.
    :param cli_arguments: arguments passed in via the CLI
    :raises SystemExit: always raised
    """
    cli_configuration = parse_cli_configuration(cli_arguments)
    configuration = read_file_configuration(cli_configuration.configuration_location)

    if cli_configuration.log_verbosity:
        logging.getLogger(PACKAGE_NAME).setLevel(cli_configuration.log_verbosity)

    docker_builder = DockerBuilder(managed_build_configurations=configuration.docker_build_configurations)
    built = docker_builder.build_all()
    print(json.dumps([image.identifier for image in built]))

    exit(0)


def entrypoint():
    """
    Entry-point to be used by CLI.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    entrypoint()
