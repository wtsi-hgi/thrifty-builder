from typing import Iterable, Dict, Generic, Optional, Any

from thriftybuilder.configurations import BuildConfigurationType


class BuildConfigurationContainer(Generic[BuildConfigurationType]):
    """
    TODO
    """
    def __init__(self, managed_build_configurations: Iterable[BuildConfigurationType]=None):
        self._build_configurations: Dict[str, BuildConfigurationType] = {}
        if managed_build_configurations is not None:
            for build_configuration in managed_build_configurations:
                self.add(build_configuration)

    def __iter__(self):
        for build_configuration in self._build_configurations:
            yield build_configuration

    def __getitem__(self, item: str):
        return self._build_configurations[item]

    def add(self, build_configuration: BuildConfigurationType):
        """
        TODO
        :param build_configuration:
        :return:
        """
        self._build_configurations[build_configuration.identifier] = build_configuration

    def remove(self, build_configuration: BuildConfigurationType):
        """
        TODO
        :param build_configuration:
        :return:
        :raises KeyError:
        """
        del self._build_configurations[build_configuration.identifier]

    def get(self, identifier: str, default: Any=None) -> Optional[BuildConfigurationType]:
        """
        TODO
        :param identifier:
        :param default:
        :return:
        """
        return self._build_configurations.get(identifier, default)
