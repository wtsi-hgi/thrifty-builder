from abc import ABCMeta
from typing import Generic

from thriftybuilder.configurations import DockerBuildConfiguration, BuildConfigurationType
from thriftybuilder.models import BuildConfigurationContainer

DEFAULT_ENCODING = "utf-8"


class BuildConfigurationManager(metaclass=ABCMeta, Generic[BuildConfigurationType]):
    """
    TODO
    """
    def __init__(self, managed_build_configurations: BuildConfigurationContainer[DockerBuildConfiguration]=None):
        self.managed_build_configurations = managed_build_configurations if managed_build_configurations is not None \
            else BuildConfigurationContainer[DockerBuildConfiguration]()
