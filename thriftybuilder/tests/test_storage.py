import os
import unittest
from abc import ABCMeta, abstractmethod
from tempfile import NamedTemporaryFile

from thriftybuilder.storage import ChecksumStorage, MemoryChecksumStorage, DiskChecksumStorage

EXAMPLE_CONFIGURATION_ID = "example-1"
EXAMPLE_CHECKSUM = "c02696b94a1787cdbe072931225d4dbc"
EXAMPLE_CONFIGURATION_ID_2 = "example-2"
EXAMPLE_CHECKSUM_2 = "f9f601085a99e4e1531bdad52771084b"


class _TestChecksumStorage(unittest.TestCase, metaclass=ABCMeta):
    """
    Tests for `ChecksumStorage` subclasses.
    """
    @abstractmethod
    def create_storage(self) -> ChecksumStorage:
        """
        Creates storage manager to be tested.
        :return: the created storage manager
        """

    def setUp(self):
        self.storage = self.create_storage()

    def test_get_all_when_none(self):
        self.assertEqual(0, len(self.storage.get_all()))

    def test_get_all(self):
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID, EXAMPLE_CHECKSUM)
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID_2, EXAMPLE_CHECKSUM_2)
        self.assertEqual({EXAMPLE_CONFIGURATION_ID: EXAMPLE_CHECKSUM, EXAMPLE_CONFIGURATION_ID_2: EXAMPLE_CHECKSUM_2},
                         self.storage.get_all())

    def test_get_when_not_set(self):
        self.assertIsNone(self.storage.get_checksum(EXAMPLE_CONFIGURATION_ID))

    def test_get_when_multiple(self):
        self.storage.set_checksum("other", "value")
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID, EXAMPLE_CHECKSUM)
        self.assertEqual(EXAMPLE_CHECKSUM, self.storage.get_checksum(EXAMPLE_CONFIGURATION_ID))

    def test_set_when_not_set(self):
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID, EXAMPLE_CHECKSUM)
        self.assertEqual({EXAMPLE_CONFIGURATION_ID: EXAMPLE_CHECKSUM}, self.storage.get_all())

    def test_set_when_set(self):
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID, "old")
        self.storage.set_checksum(EXAMPLE_CONFIGURATION_ID, EXAMPLE_CHECKSUM)
        self.assertEqual({EXAMPLE_CONFIGURATION_ID: EXAMPLE_CHECKSUM}, self.storage.get_all())


class TestMemoryChecksumStorage(_TestChecksumStorage):
    """
    Tests for `MemoryChecksumStorage`.
    """
    def create_storage(self) -> ChecksumStorage:
        return MemoryChecksumStorage()


class TestDiskChecksumStorage(_TestChecksumStorage):
    """
    Tests for `DiskChecksumStorage`.
    """
    def setUp(self):
        self._temp_file = NamedTemporaryFile().name
        super().setUp()

    def tearDown(self):
        if os.path.exists(self._temp_file):
            os.remove(self._temp_file)

    def create_storage(self) -> ChecksumStorage:
        return DiskChecksumStorage(self._temp_file)


del _TestChecksumStorage

if __name__ == "__main__":
    unittest.main()
