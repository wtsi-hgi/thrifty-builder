import hashlib
from abc import ABCMeta, abstractmethod

from typing import Union

from thriftybuilder.common import DEFAULT_ENCODING


class Hasher(metaclass=ABCMeta):
    """
    Hash calculators.
    """
    @abstractmethod
    def update(self, content: Union[str, bytes]) -> "Hasher":
        """
        Accumulate the given input.
        :param content: the input to consider when generating the cache
        """

    @abstractmethod
    def generate(self) -> str:
        """
        Generate a hash for the accumulated inputs.
        :return: the input hash
        """


class Md5Hasher(Hasher):
    """
    MD5 hash calculator.
    """
    def __init__(self):
        super().__init__()
        self._md5 = hashlib.md5()

    def update(self, content: Union[str, bytes]) -> "Md5Hasher":
        if isinstance(content, str):
            content = content.encode(DEFAULT_ENCODING)
        self._md5.update(content)
        return self

    def generate(self) -> str:
        return self._md5.hexdigest()
