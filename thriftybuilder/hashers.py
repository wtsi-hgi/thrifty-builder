import hashlib
from abc import ABCMeta, abstractmethod
from typing import Union

from thriftybuilder.common import DEFAULT_ENCODING


class Hasher(metaclass=ABCMeta):
    """
    Hash calculators.
    """
    @abstractmethod
    def update(self, input: Union[str, bytes]) -> "Hasher":
        """
        Accumulate the given input.
        :param input: the input to consider when generating the cache
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
        self._md5 = hashlib.md5()

    def update(self, input: Union[str, bytes]) -> "Md5Hasher":
        if isinstance(input, str):
            input = input.encode(DEFAULT_ENCODING)
        self._md5.update(input)
        return self

    def generate(self) -> str:
        return self._md5.hexdigest()
