from abc import ABCMeta


class ThriftyBuilderBaseError(Exception, metaclass=ABCMeta):
    """
    Base exception for package.
    """


class InvalidBuildConfigurationError(ThriftyBuilderBaseError):
    """
    Exception raised if a build configuration is invalid.
    """
