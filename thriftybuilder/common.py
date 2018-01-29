from abc import ABCMeta

DEFAULT_ENCODING = "utf-8"


class ThriftyBuilderBaseError(Exception, metaclass=ABCMeta):
    """
    Base exception for package.
    """


class MissingOptionalDependencyError(ThriftyBuilderBaseError):
    """
    Exception raised if option dependency is required but not installed.
    """
