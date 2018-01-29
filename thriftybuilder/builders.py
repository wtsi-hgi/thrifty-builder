from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from typing import Generic, TypeVar, Iterable, Set, Dict

from docker import APIClient

from thriftybuilder._logging import create_logger
from thriftybuilder.checksums import DockerChecksumCalculator, ChecksumCalculator
from thriftybuilder.common import ThriftyBuilderBaseError
from thriftybuilder.build_configurations import DockerBuildConfiguration, BuildConfigurationType, \
    BuildConfigurationManager
from thriftybuilder.storage import ChecksumStorage, MemoryChecksumStorage

BuildResultType = TypeVar("BuildResultType")

logger = create_logger(__name__)


class ThriftyBuilderBuildError(ThriftyBuilderBaseError):
    """
    Base class for errors raised during build.
    """


class CircularDependencyBuildError(ThriftyBuilderBuildError):
    """
    Error raised when circular dependency detected.
    """


class UnmanagedBuildError(ThriftyBuilderBuildError):
    """
    Error raised when illegally trying to use an un-managed build.
    """


class Builder(Generic[BuildConfigurationType, BuildResultType], BuildConfigurationManager[BuildConfigurationType],
              metaclass=ABCMeta):
    """
    Builder of items defined by the given build configuration type.
    """
    @abstractmethod
    def _build(self, build_configuration: BuildConfigurationType) -> BuildResultType:
        """
        Builds the given build configuration, given that its build dependencies have already been built.
        :param build_configuration: the configuration to build
        :return: the result of building the given configuration
        """

    def __init__(self, managed_build_configurations: Iterable[BuildConfigurationType]=None,
                 checksum_storage: ChecksumStorage=None,
                 checksum_calculator: ChecksumCalculator[BuildConfigurationType]=None):
        """
        TODO
        :param managed_build_configurations:
        :param checksum_storage:
        :param checksum_calculator:
        """
        super().__init__(managed_build_configurations)
        self.checksum_storage = checksum_storage if checksum_storage is not None else MemoryChecksumStorage()
        self.checksum_calculator = checksum_calculator

    def build(self, build_configuration: BuildConfigurationType,
              allowed_builds: Iterable[BuildConfigurationType]=None, _building: Set[BuildConfigurationType]=None) \
            -> Dict[BuildConfigurationType, BuildResultType]:
        """
        Builds the given build configuration, including any (allowed and managed) dependencies.
        :param build_configuration: the configuration to build
        :param allowed_builds: dependencies that can get built in order to build the configuration. If set
        to `None`, all dependencies will be built (default)
        :param _building: internal use only (tracks build stack to detect circular dependencies)
        :return: mapping between built configurations and their associated build result
        :raises UnmanagedBuildError: when requested to potentially build an unmanaged build
        :raises CircularDependencyBuildError: when circular dependency in FROM image
        """
        if build_configuration not in self.managed_build_configurations:
            raise UnmanagedBuildError(f"Build configuration {build_configuration} cannot be built as it is not in the "
                                      f"set of managed build configurations")

        allowed_builds = set(allowed_builds if allowed_builds is not None else self.managed_build_configurations)
        allowed_builds.add(build_configuration)
        if not allowed_builds.issubset(self.managed_build_configurations):
            raise UnmanagedBuildError(
                f"Allowed builds is not a subset of managed build configurations. Unmanaged builds in `allowed_build`: "
                f"{allowed_builds.difference(self.managed_build_configurations)}")

        _building = _building if _building is not None else set()

        if self._already_up_to_date(build_configuration):
            return {}

        build_results: OrderedDict[BuildConfigurationType: BuildResultType] = OrderedDict()
        for required_build_configuration_identifier in build_configuration.requires:
            required_build_configuration = self.managed_build_configurations.get(
                required_build_configuration_identifier, default=None)

            if required_build_configuration in allowed_builds \
                    and not self._already_up_to_date(required_build_configuration):
                left_allowed_builds = allowed_builds - set(build_results.keys())

                if required_build_configuration in _building:
                    raise CircularDependencyBuildError(
                        f"Circular dependency detected on {required_build_configuration.identifier}")

                _building.add(required_build_configuration)
                parent_build_results = self.build(required_build_configuration, left_allowed_builds, _building)
                _building.remove(required_build_configuration)
                assert set(build_results.keys()).isdisjoint(parent_build_results)
                build_results.update(parent_build_results)

        build_result = self._build(build_configuration)
        assert build_configuration not in build_results
        build_results[build_configuration] = build_result
        assert set(build_results.keys()).issubset(allowed_builds)
        return build_results

    def build_all(self) -> Dict[BuildConfigurationType, BuildResultType]:
        """
        Builds all managed images and their managed dependencies.
        :return: mapping between built configurations and their associated build result
        """
        logger.info("Building all...")

        all_build_results: Dict[BuildConfigurationType: BuildResultType] = {}
        left_to_build: Set[BuildConfigurationType] = set(self.managed_build_configurations)

        while len(left_to_build) != 0:
            build_configuration = left_to_build.pop()
            assert build_configuration not in all_build_results.keys()

            build_results = self.build(build_configuration, left_to_build)
            all_build_results.update(build_results)
            left_to_build = left_to_build - set(build_results.keys())

        logger.info(f"Built: {all_build_results}")
        return all_build_results

    def _already_up_to_date(self, build_configuration: BuildConfigurationType) -> bool:
        """
        Gets whether the image built from the given build configuration is already up-to-date according to the checksum
        store.
        :param build_configuration: the configuration to check
        :return: whether the image associated to the configuration is already up to date
        """
        existing_checksum = self.checksum_storage.get_checksum(build_configuration.identifier)
        if existing_checksum is None:
            return False

        current_checksum = self.checksum_calculator.calculate_checksum(build_configuration)
        up_to_date = existing_checksum == current_checksum
        # TODO: this assumes that all of the Docker registries contain the correct image...
        logger.debug(f"Determined that \"{build_configuration.identifier}\" is "
                     f"{'' if up_to_date else ' not'} up-to-date (checksum={current_checksum})")
        return up_to_date


class DockerBuilder(Builder[DockerBuildConfiguration, str]):
    """
    Builder of Docker images.
    """
    def __init__(self, managed_build_configurations: Iterable[BuildConfigurationType]=None,
                 checksum_storage: ChecksumStorage=None,
                 checksum_calculator: ChecksumCalculator[DockerBuildConfiguration]=None):
        checksum_calculator = checksum_calculator if checksum_calculator is not None else DockerChecksumCalculator()
        super().__init__(managed_build_configurations, checksum_storage, checksum_calculator)
        self._docker_client = APIClient()

    def __del__(self):
        self._docker_client.close()

    def _build(self, build_configuration: DockerBuildConfiguration) -> str:
        logger.info(f"Building Docker image: {build_configuration.identifier}")
        logger.debug(f"{build_configuration.identifier} to be built using dockerfile "
                     f"\"{build_configuration.dockerfile_location}\" in context \"{build_configuration.context}\"")
        log_generator = self._docker_client.build(path=build_configuration.context, tag=build_configuration.identifier,
                                                  dockerfile=build_configuration.dockerfile_location, decode=True)

        for log in log_generator:
            details = log.get("stream", "").strip()
            if len(details) > 0:
                logger.debug(details)

        return build_configuration.identifier
