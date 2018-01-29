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

EXAMPLE_1_CONFIGURATION_ID = "example-configuration-id-1"
EXAMPLE_1_CHECKSUM = "c02696b94a1787cdbe072931225d4dbc"
EXAMPLE_2_CONFIGURATION_ID = "example-configuration-id-2"
EXAMPLE_2_CHECKSUM = "f9f601085a99e4e1531bdad52771084b"

EXAMPLE_1_CONSUL_KEY = "example-key-1"
EXAMPLE_2_CONSUL_KEY = "example-key-2"


def name_generator(identifier: str= "") -> str:
    """
    Generates a unique name.
    :param identifier: identifier to add to the name
    :return: the generated name
    """
    return f"thrifty-builder-test-{identifier}{uuid4()}"
