from typing import Set, Generic

from thriftybuilder.configurations import BuildConfigurationType


class Builder(Generic[BuildConfigurationType]):
    """
    TODO
    """
    def __init__(self):
        """
        TODO
        """
        self.configurations: Set[BuildConfigurationType] = set()

    def build(self):
        pass