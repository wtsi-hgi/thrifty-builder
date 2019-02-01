import os
from abc import ABCMeta
from typing import List, Iterable

DEFAULT_ENCODING = "utf-8"


class ThriftyBuilderBaseError(Exception, metaclass=ABCMeta):
    """
    Base exception for package.
    """


class MissingOptionalDependencyError(ThriftyBuilderBaseError):
    """
    Exception raised if option dependency is required but not installed.
    """


def walk_directory(directory_path: str) -> List[str]:
    return list(walk_directory_generator(directory_path))


def walk_directory_generator(directory_path: str) -> Iterable[str]:
    for root, directories, files in os.walk(directory_path):
        for name in files + directories:
            yield (os.path.join(root, name))
