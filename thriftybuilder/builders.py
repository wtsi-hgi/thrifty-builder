from abc import ABCMeta, abstractmethod
from collections import OrderedDict

from docker import APIClient
from docker.errors import APIError
from typing import Generic, TypeVar, Iterable, Set, Dict, Callable, Optional

from thriftybuilder._logging import create_logger
from thriftybuilder.build_configurations import DockerBuildConfiguration, BuildConfigurationType, \
    BuildConfigurationManager
from thriftybuilder.checksums import DockerChecksumCalculator, ChecksumCalculator
from thriftybuilder.common import ThriftyBuilderBaseError
from thriftybuilder.storage import ChecksumStorage, MemoryChecksumStorage, ChecksumRetriever, \
    DoubleSourceChecksumStorage

BuildResultType = TypeVar("BuildResultType")
ChecksumCalculatorType = TypeVar("ChecksumCalculatorType", bound=ChecksumCalculator[BuildConfigurationType])

logger = create_logger(__name__)


class ThriftyBuilderError(ThriftyBuilderBaseError):
    """
    Base class for errors raised during build.
    """


class CircularDependencyBuildError(ThriftyBuilderError):
    """
    Error raised when circular dependency detected.
    """


class UnmanagedBuildError(ThriftyBuilderError):
    """
    Error raised when illegally trying to use an un-managed build.
    """


class BuildFailedError(ThriftyBuilderError):
    """
    Error raised if error occurs during build.
    """
    def __init__(self, image_name: str, message: str=None):
        super().__init__(message)
        self.image_name = image_name


class InvalidDockerfileBuildError(BuildFailedError):
    """
    Error raised when Dockerfile is invalid.
    """
    def __init__(self, image_name: str, dockerfile_location: str, contents: str):
        super().__init__(image_name, message=f"Invalid Dockerfile for {image_name}: {dockerfile_location}")
        self.dockerfile_location = dockerfile_location
        self.contents = contents


class BuildStepError(BuildFailedError):
    """
    Error raised if error occurs during a build step.
    """
    def __init__(self, image_name: str, error_message: str, exit_code: Optional[int]):
        super().__init__(
            image_name, message=f"Build for {image_name} failed with exit code {exit_code}: {error_message}")
        self.error_message = error_message
        self.exit_code = exit_code


class Builder(Generic[BuildConfigurationType, BuildResultType, ChecksumCalculatorType],
              BuildConfigurationManager[BuildConfigurationType], metaclass=ABCMeta):
    """
    Builder of items defined by the given build configuration type.
    """
    @abstractmethod
    def _build(self, build_configuration: BuildConfigurationType) -> BuildResultType:
        """
        Builds the given build configuration, given that its build dependencies have already been built.
        :param build_configuration: the configuration to build
        :return: the result of building the given configuration
        :raises BuildFailedError: raised if the build fails
        """

    def __init__(self, managed_build_configurations: Iterable[BuildConfigurationType]=None,
                 checksum_retriever: ChecksumRetriever=None,
                 checksum_calculator_factory: Callable[[], ChecksumCalculatorType]=None):
        """
        Constructor.
        :param managed_build_configurations: build configurations that are managed by this builder
        :param checksum_retriever: checksum retriever
        :param checksum_calculator_factory: callable that returns a checksum calculator
        """
        super().__init__(managed_build_configurations)
        self.checksum_retriever = checksum_retriever if checksum_retriever is not None else MemoryChecksumStorage()
        self.checksum_calculator = checksum_calculator_factory()

    def build(self, build_configuration: BuildConfigurationType,
              allowed_builds: Iterable[BuildConfigurationType]=None, *, _building: Set[BuildConfigurationType]=None,
              _checksum_storage: ChecksumStorage=None) \
            -> Dict[BuildConfigurationType, BuildResultType]:
        """
        Builds the given build configuration, including any (allowed and managed) dependencies.
        :param build_configuration: the configuration to build
        :param allowed_builds: dependencies that can get built in order to build the configuration. If set
        to `None`, all dependencies will be built (default)
        :param _building: internal use only (tracks build stack to detect circular dependencies)
        :param _checksum_storage: internal use only (has checksums of newly built configurations)
        :return: mapping between built configurations and their associated build result
        :raises UnmanagedBuildError: when requested to potentially build an unmanaged build
        :raises CircularDependencyBuildError: when circular dependency in FROM image
        :raises BuildFailedError: raised if the build fails
        """
        if build_configuration not in self.managed_build_configurations:
            raise UnmanagedBuildError(f"Build configuration {build_configuration} cannot be built as it is not in the "
                                      f"set of managed build configurations")

        building = _building if _building is not None else set()
        checksum_storage = _checksum_storage if _checksum_storage is not None else self.checksum_retriever
        allowed_builds = set(allowed_builds if allowed_builds is not None else self.managed_build_configurations)

        # Storing checksums of updated dependency builds
        checksum_storage = DoubleSourceChecksumStorage(MemoryChecksumStorage(), checksum_storage)

        # Manage collection of what configurations can be built
        allowed_builds.add(build_configuration)
        if not allowed_builds.issubset(self.managed_build_configurations):
            raise UnmanagedBuildError(
                f"Allowed builds is not a subset of managed build configurations. Unmanaged builds in `allowed_build`: "
                f"{allowed_builds.difference(self.managed_build_configurations)}")

        if self._already_up_to_date(build_configuration):
            return {}

        # TODO: Break dependency build into separate function
        # Build dependent configurations
        build_results: OrderedDict[BuildConfigurationType: BuildResultType] = OrderedDict()
        for required_build_configuration_identifier in build_configuration.requires:
            required_build_configuration = self.managed_build_configurations.get(
                required_build_configuration_identifier, default=None)

            if required_build_configuration in allowed_builds \
                    and not self._already_up_to_date(required_build_configuration):
                left_allowed_builds = allowed_builds - set(build_results.keys())

                if required_build_configuration in building:
                    raise CircularDependencyBuildError(
                        f"Circular dependency detected on {required_build_configuration.identifier}")

                # Build dependency ("parent")
                building.add(required_build_configuration)
                parent_build_results = self.build(required_build_configuration, left_allowed_builds,
                                                  _building=building, _checksum_storage=checksum_storage)
                building.remove(required_build_configuration)

                # Store dependency build results
                assert set(build_results.keys()).isdisjoint(parent_build_results)
                build_results.update(parent_build_results)

                # Update known configuration checksums
                checksums = {x.identifier: self.checksum_calculator.calculate_checksum(x) for x in build_results.keys()}
                checksum_storage.set_all_checksums(checksums)

        # Build main configuration
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

        checksum_storage = DoubleSourceChecksumStorage(MemoryChecksumStorage(), self.checksum_retriever)

        all_build_results: Dict[BuildConfigurationType: BuildResultType] = {}
        left_to_build: Set[BuildConfigurationType] = set(self.managed_build_configurations)

        while len(left_to_build) != 0:
            build_configuration = left_to_build.pop()
            assert build_configuration not in all_build_results.keys()

            # Build configuration
            build_results = self.build(build_configuration, left_to_build, _checksum_storage=checksum_storage)
            all_build_results.update(build_results)

            # Update known configuration checksums
            checksums = {x.identifier: self.checksum_calculator.calculate_checksum(x) for x in build_results.keys()}
            checksum_storage.set_all_checksums(checksums)

            left_to_build = left_to_build - set(build_results.keys())

        logger.info(f"Built: {all_build_results}")
        return all_build_results

    def _already_up_to_date(self, build_configuration: BuildConfigurationType, *,
                            _checksum_retriever: ChecksumRetriever=None) -> bool:
        """
        Gets whether the image built from the given build configuration is already up-to-date according to the checksum
        store.
        :param build_configuration: the configuration to check
        :param _checksum_retriever: internal use only
        :return: whether the image associated to the configuration is already up to date
        """
        checksum_retriever = _checksum_retriever if _checksum_retriever is not None else self.checksum_retriever
        existing_checksum = checksum_retriever.get_checksum(build_configuration.identifier)
        if existing_checksum is None:
            return False

        current_checksum = self.checksum_calculator.calculate_checksum(build_configuration)
        up_to_date = existing_checksum == current_checksum
        # TODO: this assumes that all of the Docker registries contain the correct image...
        logger.debug(f"Determined that \"{build_configuration.identifier}\" is "
                     f"{'' if up_to_date else ' not'} up-to-date (checksum={current_checksum}"
                     f"{'' if up_to_date else f' != ' + existing_checksum})")
        return up_to_date


class DockerBuilder(Builder[DockerBuildConfiguration, str, DockerChecksumCalculator]):
    """
    Builder of Docker images.
    """
    def __init__(self, managed_build_configurations: Iterable[BuildConfigurationType]=None,
                 checksum_retriever: ChecksumRetriever=None,
                 checksum_calculator_factory: Callable[[], DockerChecksumCalculator]=DockerChecksumCalculator):
        super().__init__(managed_build_configurations, checksum_retriever, checksum_calculator_factory)
        self.checksum_calculator.managed_build_configurations = self.managed_build_configurations
        self._docker_client = APIClient()

    def __del__(self):
        self._docker_client.close()

    def _build(self, build_configuration: DockerBuildConfiguration) -> str:
        logger.info(f"Building Docker image: {build_configuration.identifier}")
        logger.debug(f"{build_configuration.identifier} to be built using dockerfile "
                     f"\"{build_configuration.dockerfile_location}\" in context \"{build_configuration.context}\"")
        log_generator = self._docker_client.build(path=build_configuration.context, tag=build_configuration.identifier,
                                                  dockerfile=build_configuration.dockerfile_location, decode=True)

        log = {}
        try:
            for log in log_generator:
                details = log.get("stream", "").strip()
                if len(details) > 0:
                    logger.debug(details)
        except APIError as e:
            if e.status_code == 400 and "parse error" in e.explanation:
                dockerfile_location = build_configuration.dockerfile_location
                with open(dockerfile_location, "r") as file:
                    raise InvalidDockerfileBuildError(build_configuration.name, dockerfile_location, file.read())
            raise e

        if "error" in log:
            error_details = log["errorDetail"]
            raise BuildStepError(build_configuration.name, error_details["message"], error_details.get("code"))

        return build_configuration.identifier
