import dockerfile
import hashlib
import itertools
import os
from abc import abstractmethod, ABCMeta
from glob import glob
from typing import List, Iterable, Set, Optional

from checksumdir import dirhash
from zgitignore import ZgitIgnore

from thriftybuilder.common import DEFAULT_ENCODING

_FROM_DOCKER_COMMAND = "from"
_ADD_DOCKER_COMMAND = "add"
_COPY_DOCKER_COMMAND = "copy"
_DOCKER_IGNORE_FILE = ".dockerignore"


class BuildConfiguration(metaclass=ABCMeta):
    """
    TODO
    """
    @property
    @abstractmethod
    def dependent_images(self) -> List[str]:
        """
        TODO
        :param build_configuration:
        :return:
        """

    @property
    @abstractmethod
    def used_files(self) -> List[str]:
        """
        TODO
        :param build_configuration:
        :return:
        """

    @abstractmethod
    def get_checksum(self) -> str:
        """
        TODO
        :return:
        """


class DockerBuildConfiguration(BuildConfiguration):
    """
    TODO
    """
    @property
    def dockerfile_location(self) -> Optional[str]:
        return self._dockerfile_location

    @property
    def dependent_images(self) -> List[str]:
        for command in self.commands:
            if command.cmd == _FROM_DOCKER_COMMAND:
                return command.value

    @property
    def used_files(self) -> Iterable[str]:
        """
        Note: does not support adding URLs.
        """
        source_patterns: List[str] = []
        for command in self.commands:
            if command.cmd in [_ADD_DOCKER_COMMAND, _COPY_DOCKER_COMMAND]:
                assert len(command.value) >= 2
                source_patterns.extend(command.value[0:-1])

        # ZGitIgnore roughly implements the same parsing of .dockerignore files as Docker:
        # https://docs.docker.com/engine/reference/builder/#dockerignore-file
        ignored_checker = ZgitIgnore(self.get_ignored_files())
        files: List[str] = []
        for source_path in source_patterns:
            full_source_path = os.path.normpath(os.path.join(os.path.dirname(self.dockerfile_location), source_path))
            if os.path.isdir(full_source_path):
                candidate_files = glob(f"{full_source_path}/**/*", recursive=True)
            else:
                candidate_files = [full_source_path]

            for file in candidate_files:
                if not os.path.isdir(file) and not ignored_checker.is_ignored(file):
                    files.append(file)

        return files

    def __init__(self, dockerfile_location: str):
        """
        TODO
        :param dockerfile_location:
        """
        self._dockerfile_location = dockerfile_location
        self.commands = dockerfile.parse_file(self.dockerfile_location)

    def get_checksum(self) -> str:
        """
        Note: does not consider file metadata when calculating checksum.
        """
        return hashlib.md5(self.get_configuration_checksum() + self.get_used_files_checksum()).hexdigest()

    def get_configuration_checksum(self) -> str:
        """
        TODO
        :return:
        """
        hash_accumulator = hashlib.md5()
        for command in self.commands:
            hash_accumulator.update(command.original.encode(DEFAULT_ENCODING))
        return hash_accumulator.hexdigest().encode(DEFAULT_ENCODING)

    def get_used_files_checksum(self) -> str:
        """
        TODO
        :return:
        """
        hash_accumulator = hashlib.md5()
        for file_path in sorted(self.used_files):
            if os.path.isdir(file_path):
                hash_accumulator.update(dirhash(file_path).encode(DEFAULT_ENCODING))
            else:
                with open(file_path, "rb") as file:
                    hash_accumulator.update(file.read())
        return hash_accumulator.hexdigest().encode(DEFAULT_ENCODING)

    def get_ignored_files(self) -> Set[str]:
        """
        TODO
        :return:
        """
        dockerignore_path = os.path.join(os.path.dirname(self.dockerfile_location), _DOCKER_IGNORE_FILE)
        if not os.path.exists(dockerignore_path):
            return set()
        with open(dockerignore_path, "r") as file:
            return {line.strip() for line in file.readlines()}

