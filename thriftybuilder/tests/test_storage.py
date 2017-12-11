import unittest
from abc import ABCMeta, abstractmethod
from tempfile import NamedTemporaryFile

import os

from thriftybuilder.storage import Storage, MemoryStorage, DiskStorage

EXAMPLE_CONFIGURATION_ID = "test123"
EXAMPLE_CHECKSUM = "c02696b94a1787cdbe072931225d4dbc"


class _TestStorage(unittest.TestCase, metaclass=ABCMeta):
    """
    Tests for `Storage` subclasses.
    """
    @abstractmethod
    def create_storage(self) -> Storage:
        """
        Creates storage manager to be tested.
        :return: the created storage manager
        """

    def setUp(self):
        self.storage = self.create_storage()

    def test_get_when_not_set(self):
        self.assertIsNone(self.storage.get_checksum(EXAMPLE_CONFIGURATION_ID))

    def test_get_when_multiple(self):
        self.storage.set_checksum("other", "value")
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID, EXAMPLE_CHECKSUM)
        self.assertEqual(EXAMPLE_CHECKSUM, self.storage.get_checksum(EXAMPLE_CONFIGURATION_ID))

    def test_set_when_not_set(self):
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID, EXAMPLE_CHECKSUM)
        self.assertEqual(EXAMPLE_CHECKSUM, self.storage.get_checksum(EXAMPLE_CONFIGURATION_ID))

    def test_set_when_set(self):
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID, "old")
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID, EXAMPLE_CHECKSUM)
        self.assertEqual(EXAMPLE_CHECKSUM, self.storage.get_checksum(EXAMPLE_CONFIGURATION_ID))


class TestMemoryStorage(_TestStorage):
    """
    Tests for `MemoryStorage`.
    """
    def create_storage(self) -> Storage:
        return MemoryStorage()


class TestDiskStorage(_TestStorage):
    """
    Tests for `DiskStorage`.
    """
    def setUp(self):
        self._temp_file = NamedTemporaryFile().name
        super().setUp()

    def tearDown(self):
        if os.path.exists(self._temp_file):
            os.remove(self._temp_file)

    def create_storage(self) -> Storage:
        return DiskStorage(self._temp_file)


del _TestStorage

if __name__ == "__main__":
    unittest.main()
