from typing import Generic, Iterable, Dict, Iterator, Optional

from thriftybuilder.build_configurations import BuildConfigurationType


class BuildConfigurationContainer(Generic[BuildConfigurationType]):
    """
    Container of build configurations.
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
        Gets the build configuration with the given identifier from this collection, returning the given default if that
        configuration does not exist.
        :param identifier: the identifier of the configuration to get
        :param default: returned if the configuration is not in the container
        :return: the required configuration or `default`
        """
        return self._build_configurations.get(identifier, default)

    def add(self, build_configuration: BuildConfigurationType):
        """
        Add the given build configuration to this collection.
        :param build_configuration: the build configuration to add
        """
        self._build_configurations[build_configuration.identifier] = build_configuration

    def add_all(self, build_configurations: Iterable[BuildConfigurationType]):
        """
        Adds the given build configurations to this collection.
        :param build_configurations: the build configurations to add
        """
        for build_configuration in build_configurations:
            self.add(build_configuration)

    def remove(self, build_configuration: BuildConfigurationType):
        """
        Removes the given build configuration from this container.
        :param build_configuration: the build configuration to remove
        :raises KeyError: raised if the build configuration does not exist
        """
        del self._build_configurations[build_configuration.identifier]