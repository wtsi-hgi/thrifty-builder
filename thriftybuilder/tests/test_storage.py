import os
import unittest
from abc import ABCMeta, abstractmethod
from tempfile import NamedTemporaryFile

from thriftybuilder.storage import ChecksumStorage, MemoryChecksumStorage, DiskChecksumStorage, ConsulChecksumStorage
from thriftybuilder.tests._common import TestWithConsulService
from thriftybuilder.tests._examples import EXAMPLE_1_CONFIGURATION_ID, EXAMPLE_1_CHECKSUM, EXAMPLE_2_CONFIGURATION_ID, \
    EXAMPLE_2_CHECKSUM, EXAMPLE_1_CONSUL_KEY, EXAMPLE_2_CONSUL_KEY


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
        super().setUp()
        self.storage = self.create_storage()

    def test_get_when_not_set(self):
        self.assertIsNone(self.storage.get_checksum(EXAMPLE_1_CONFIGURATION_ID))

    def test_get_when_multiple(self):
        self.storage.set_checksum("other", "value")
        self.storage.set_checksum(EXAMPLE_1_CONFIGURATION_ID, EXAMPLE_1_CHECKSUM)
        self.assertEqual(EXAMPLE_1_CHECKSUM, self.storage.get_checksum(EXAMPLE_1_CONFIGURATION_ID))

    def test_get_all_checksums_when_none(self):
        self.assertEqual(0, len(self.storage.get_all_checksums()))

    def test_get_all_checksums(self):
        self.storage.set_checksum(EXAMPLE_1_CONFIGURATION_ID, EXAMPLE_1_CHECKSUM)
        self.storage.set_checksum(EXAMPLE_2_CONFIGURATION_ID, EXAMPLE_2_CHECKSUM)
        self.assertEqual({EXAMPLE_1_CONFIGURATION_ID: EXAMPLE_1_CHECKSUM, EXAMPLE_2_CONFIGURATION_ID: EXAMPLE_2_CHECKSUM},
                         self.storage.get_all_checksums())

    def test_set_when_not_set(self):
        self.storage.set_checksum(EXAMPLE_1_CONFIGURATION_ID, EXAMPLE_1_CHECKSUM)
        self.assertEqual({EXAMPLE_1_CONFIGURATION_ID: EXAMPLE_1_CHECKSUM}, self.storage.get_all_checksums())

    def test_set_when_set(self):
        self.storage.set_checksum(EXAMPLE_1_CONFIGURATION_ID, "old")
        self.storage.set_checksum(EXAMPLE_1_CONFIGURATION_ID, EXAMPLE_1_CHECKSUM)
        self.assertEqual({EXAMPLE_1_CONFIGURATION_ID: EXAMPLE_1_CHECKSUM}, self.storage.get_all_checksums())

    def test_set_all_checksums(self):
        self.storage.set_all_checksums(
            {EXAMPLE_1_CONFIGURATION_ID: EXAMPLE_1_CHECKSUM, EXAMPLE_2_CONFIGURATION_ID: EXAMPLE_2_CHECKSUM})
        self.assertEqual(EXAMPLE_1_CHECKSUM, self.storage.get_checksum(EXAMPLE_1_CONFIGURATION_ID))
        self.assertEqual(EXAMPLE_2_CHECKSUM, self.storage.get_checksum(EXAMPLE_2_CONFIGURATION_ID))


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


class TestConsulChecksumStorage(_TestChecksumStorage, TestWithConsulService):
    """
    Tests for `ConsulChecksumStorage`.
    """
    def create_storage(self) -> ChecksumStorage:
        return ConsulChecksumStorage(EXAMPLE_1_CONSUL_KEY, EXAMPLE_2_CONSUL_KEY, consul_client=self.consul_client)

    def test_create_init_with_explicit_configuration(self):
        storage = ConsulChecksumStorage(EXAMPLE_1_CONSUL_KEY, EXAMPLE_2_CONSUL_KEY,
                                        url=self.consul_client.http.base_uri, token=self.consul_client.token)
        storage.set_checksum(EXAMPLE_1_CONFIGURATION_ID, EXAMPLE_1_CHECKSUM)
        self.assertEqual(EXAMPLE_1_CHECKSUM, storage.get_checksum(EXAMPLE_1_CONFIGURATION_ID))


del _TestChecksumStorage

if __name__ == "__main__":
    unittest.main()
