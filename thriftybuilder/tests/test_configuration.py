import os

from thriftybuilder.configuration import Configuration, DockerRegistry, read_configuration
from thriftybuilder.tests._common import TestWithConfiguration

_EXAMPLE_URL_1 = "example-url-1"
_EXAMPLE_USERNAME_1 = "example-username-1"
_EXAMPLE_PASSWORD_1 = "example-password-1"


class TestReadConfiguration(TestWithConfiguration):
    """
    Tests for `read_configuration`.
    """
    def test_with_template(self):
        registry = DockerRegistry(_EXAMPLE_URL_1, "{{ env['EXAMPLE_USERNAME_1'] }}", "{{ env['EXAMPLE_PASSWORD_1'] }}")
        configuration = Configuration(docker_registries=(registry, ))
        configuration_location = self.configuration_to_file(configuration)

        os.environ["EXAMPLE_USERNAME_1"] = _EXAMPLE_USERNAME_1
        os.environ["EXAMPLE_PASSWORD_1"] = _EXAMPLE_PASSWORD_1

        configuration = read_configuration(configuration_location)
        self.assertEqual(1, len(configuration.docker_registries))
        registry = configuration.docker_registries[0]
        self.assertEqual(_EXAMPLE_URL_1, registry.url)
        self.assertEqual(_EXAMPLE_USERNAME_1, registry.username)
        self.assertEqual(_EXAMPLE_PASSWORD_1, registry.password)
