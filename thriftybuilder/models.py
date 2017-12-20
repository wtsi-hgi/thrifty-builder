from typing import Iterable, Dict, Generic, Optional, Iterator

from thriftybuilder.configurations import BuildConfigurationType


class BuildConfigurationContainer(Generic[BuildConfigurationType]):
    """
    TODO
    """
    def __init__(self, managed_build_configurations: Iterable[BuildConfigurationType]=None):
        self._build_configurations: Dict[str, BuildConfigurationType] = {}
        if managed_build_configurations is not None:
            self.add_all(managed_build_configurations)

    def __iter__(self) -> Iterator[BuildConfigurationType]:
        for build_configuration in self._build_configurations.values():
            yield build_configuration

    def __getitem__(self, item: str) -> BuildConfigurationType:
        return self._build_configurations[item]

    def __len__(self) -> int:
        return len(self._build_configurations)

    def __str__(self) -> str:
        return str(self._build_configurations)

    def get(self, identifier: str, default: Optional[BuildConfigurationType]=None) -> Optional[BuildConfigurationType]:
        """
        TODO
        :param identifier:
        :param default:
        :return:
        """
        return self._build_configurations.get(identifier, default)

    def add(self, build_configuration: BuildConfigurationType):
        """
        TODO
        :param build_configuration:
        :return:
        """
        self._build_configurations[build_configuration.identifier] = build_configuration

    def add_all(self, build_configurations: Iterable[BuildConfigurationType]):
        """
        TODO
        :param build_configurations:
        :return:
        """
        for build_configuration in build_configurations:
            self.add(build_configuration)

    def remove(self, build_configuration: BuildConfigurationType):
        """
        TODO
        :param build_configuration:
        :return:
        :raises KeyError:
        """
        del self._build_configurations[build_configuration.identifier]
