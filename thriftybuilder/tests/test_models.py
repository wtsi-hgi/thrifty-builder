from thriftybuilder.configurations import DockerBuildConfiguration
from thriftybuilder.models import BuildConfigurationContainer
from thriftybuilder.tests._common import TestWithDockerBuildConfiguration


class TestBuildConfigurationContainer(TestWithDockerBuildConfiguration):
    """
    Tests for `BuildConfigurationContainer`.
    """
    def setUp(self):
        super().setUp()
        _, self.configuration = self.create_docker_setup()
        self.container = BuildConfigurationContainer[DockerBuildConfiguration]()

    def test_setup_with_items(self):
        configurations = [self.create_docker_setup(image_name=i)[1] for i in range(5)]
        container = BuildConfigurationContainer(configurations)
        self.assertCountEqual(configurations, container)

    def test_len(self):
        length = 5
        self.container.add_all([self.create_docker_setup(image_name=i)[1] for i in range(length)])
        self.assertEqual(length, len(self.container))

    def test_index_when_not_added(self):
        _, default = self.create_docker_setup()
        try:
            self.container[self.configuration.identifier]
        except KeyError:
            pass

    def test_index(self):
        self.container.add(self.configuration)
        self.assertEqual(self.configuration, self.container[self.configuration.identifier])

    def test_get_when_not_added(self):
        _, default = self.create_docker_setup()
        self.assertEqual(default, self.container.get(self.configuration.identifier, default=default))

    def test_get(self):
        self.container.add(self.configuration)
        self.assertEqual(self.configuration, self.container.get(self.configuration.identifier))

    def test_add_when_not_added(self):
        self.container.add(self.configuration)
        self.assertCountEqual([self.configuration], self.container)

    def test_add_when_added(self):
        _, configuration_2 = self.create_docker_setup(image_name=self.configuration.identifier)
        self.container.add(self.configuration)
        self.container.add(configuration_2)
        self.assertCountEqual([configuration_2], self.container)

    def test_add_all(self):
        configurations = [self.create_docker_setup(image_name=i)[1] for i in range(5)]
        self.container.add_all(configurations)
        self.assertCountEqual(configurations, self.container)

    def test_remove_when_not_added(self):
        self.assertRaises(KeyError, self.container.remove, self.configuration)

    def test_remove(self):
        self.container.add(self.configuration)
        assert len(self.container) == 1 and self.container[self.configuration.identifier] == self.configuration
        self.container.remove(self.configuration)
        self.assertEqual(0, len(self.container))
