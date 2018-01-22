from abc import ABCMeta
from typing import Generic, Iterable

from thriftybuilder.build_configurations import BuildConfigurationType
from thriftybuilder.containers import BuildConfigurationContainer

DEFAULT_ENCODING = "utf-8"


class BuildConfigurationManager(Generic[BuildConfigurationType], metaclass=ABCMeta):
    """
    A class that manages a collection of build configurations.
    """
    def __init__(self, managed_build_configurations: Iterable[BuildConfigurationType]=None):
        initial_configurations = managed_build_configurations if managed_build_configurations is not None else ()
        self.managed_build_configurations = BuildConfigurationContainer[BuildConfigurationType](initial_configurations)
