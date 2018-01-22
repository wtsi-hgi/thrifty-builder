from uuid import uuid4

from thriftybuilder.tests._common import RUN_DOCKER_COMMAND

EXAMPLE_IMAGE_NAME = "hello-world-test"
EXAMPLE_FROM_IMAGE_NAME = "alpine"
EXAMPLE_IMAGE_NAME_1 = "example-1"
EXAMPLE_IMAGE_NAME_2 = "example-2"

EXAMPLE_FILE_NAME_1 = "example-1"
EXAMPLE_FILE_CONTENTS_1 = "testing1"
EXAMPLE_FILE_NAME_2 = "example-2"
EXAMPLE_FILE_CONTENTS_2 = "testing2"

EXAMPLE_RUN_COMMAND = f"{RUN_DOCKER_COMMAND} echo test"


def name_generator(identifier: str= "") -> str:
    """
    Generates a unique name.
    :param identifier: identifier to add to the name
    :return: the generated name
    """
    return f"thrifty-builder-test-{identifier}{uuid4()}"
