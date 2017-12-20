from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar, Tuple, Iterable, Set, Dict

import docker

from thriftybuilder.common import BuildConfigurationManager
from thriftybuilder.configurations import BuildConfigurationType, DockerBuildConfiguration

BuildResultType = TypeVar("BuildResultType")


class Builder(Generic[BuildConfigurationType, BuildResultType], BuildConfigurationManager[BuildConfigurationType],
              metaclass=ABCMeta):
    """
    TODO
    """
    @abstractmethod
    def _build(self, build_configuration: BuildConfigurationType) -> BuildResultType:
        """
        TODO
        :return:
        """

    def build(self, build_configuration: BuildConfigurationType,
              allowed_dependency_builds: Iterable[BuildConfigurationType]=None) \
            -> Dict[BuildConfigurationType, BuildResultType]:
        """
        TODO
        :param build_configuration:
        :param allowed_dependency_builds:
        :return:
        """
        allowed_dependency_builds = set(allowed_dependency_builds if allowed_dependency_builds is not None
                                        else self.managed_build_configurations)
        allowed_dependency_builds.add(build_configuration)
        build_results: Dict[BuildConfigurationType: BuildResultType] = {}

        for required_build_configuration_identifier in build_configuration.requires:
            required_build_configuration = self.managed_build_configurations.get(
                required_build_configuration_identifier, default=None)
            if required_build_configuration is not None and required_build_configuration in allowed_dependency_builds:
                parent_build_results = self.build(required_build_configuration)
                build_results.update(parent_build_results)

        build_result = self._build(build_configuration)
        assert build_configuration not in build_results
        build_results[build_configuration] = build_result
        assert set(build_results.keys()).issubset(allowed_dependency_builds)
        return build_results

    def build_all(self) -> Dict[BuildConfigurationType, BuildResultType]:
        """
        TODO
        :return:
        """
        all_build_results: Dict[BuildConfigurationType: BuildResultType] = {}
        left_to_build: Set[BuildConfigurationType] = set(self.managed_build_configurations)

        while len(left_to_build) != 0:
            build_configuration = left_to_build.pop()

            for required_build_configuration_identifier in build_configuration.requires:
                required_build_configuration = self.managed_build_configurations.get(
                    required_build_configuration_identifier, default=None)
                if required_build_configuration in left_to_build:
                    dependency_build_results = self.build(required_build_configuration, left_to_build)
                    all_build_results.update(dependency_build_results)
                    for dependency_build_configuration in dependency_build_results.keys():
                        left_to_build.remove(dependency_build_configuration)

            assert build_configuration not in all_build_results.keys(), \
                f"Circular build dependency on {build_configuration.identifier}"
            build_results = self._build(build_configuration)
            all_build_results.update({build_configuration: build_results})

        return all_build_results


class DockerBuilder(Builder[DockerBuildConfiguration, str]):
    """
    TODO
    """
    def __init__(self):
        super().__init__()
        self._docker_client = docker.from_env()

    def _build(self, build_configuration: DockerBuildConfiguration) -> str:
        # TODO: Consider setting `cache_from`: https://docker-py.readthedocs.io/en/stable/images.html
        self._docker_client.images.build(path=build_configuration.context, tag=build_configuration.identifier,
                                         dockerfile=build_configuration.dockerfile_location)
        return build_configuration.identifier
