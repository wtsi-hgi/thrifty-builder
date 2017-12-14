import dockerfile
import os
from abc import abstractmethod, ABCMeta
from glob import glob
from typing import List, Iterable, Set, Optional, TypeVar

from zgitignore import ZgitIgnore

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
    def identifier(self) -> str:
        """
        TODO
        :return:
        """

    @property
    @abstractmethod
    def requires(self) -> List[str]:
        """
        TODO
        :return:
        """

    @property
    @abstractmethod
    def used_files(self) -> List[str]:
        """
        TODO
        :return:
        """


BuildConfigurationType = TypeVar("BuildConfigurationType", bound=BuildConfiguration)


class DockerBuildConfiguration(BuildConfiguration):
    """
    TODO
    """
    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def requires(self) -> List[str]:
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

    @property
    def from_image(self) -> str:
        """
        TODO
        :return:
        """
        return self.requires[0]

    @property
    def dockerfile_location(self) -> Optional[str]:
        return self._dockerfile_location

    @property
    def context(self) -> str:
        return self._context

    def __init__(self, image_name: str, dockerfile_location: str, context: str=None):
        """
        TODO
        :param image_name:
        :param dockerfile_location:
        :param context:
        """
        self._identifier = image_name
        self._dockerfile_location = dockerfile_location
        self._context = context if context is None else os.path.dirname(self.dockerfile_location)
        self.commands = dockerfile.parse_file(self.dockerfile_location)

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
