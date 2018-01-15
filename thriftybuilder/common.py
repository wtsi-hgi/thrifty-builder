from abc import ABCMeta
from typing import Generic

from thriftybuilder.models import BuildConfigurationContainer, BuildConfigurationType

DEFAULT_ENCODING = "utf-8"


class BuildConfigurationManager(Generic[BuildConfigurationType], metaclass=ABCMeta):
    """
    A class that manages a collection of build configurations.
    """
    def __init__(self, managed_build_configurations: BuildConfigurationContainer[BuildConfigurationType]=None):
        self.managed_build_configurations = managed_build_configurations if managed_build_configurations is not None \
            else BuildConfigurationContainer[BuildConfigurationType]()
