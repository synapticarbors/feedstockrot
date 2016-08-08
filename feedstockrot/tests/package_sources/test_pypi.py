from unittest import TestCase
from feedstockrot.package_sources.pypi import Pypi
import responses
from feedstockrot.package import Package
from ..helpers.condaforge import mock_repodata
from ..helpers.pypi import mock_pypi


class TestPypi(TestCase):

    def test_possible_names(self):
        name = 'testing'
        package_names = {
            '{}-python'.format(name), '{}-py'.format(name),
            'python-{}'.format(name), 'py-{}'.format(name)
        }

        for package_name in package_names:
            possible = Pypi._possible_names(package_name)
            self.assertListEqual(
                [package_name, name],
                possible
            )

    def test_fetch_versions(self):
        pkg_name = 'package_a'

        with mock_pypi(pkg_name):
            result = Pypi._fetch_versions(pkg_name)

        self.assertIsNotNone(result)

    def test_versions(self):
        pkg = Package('package_a')

        with mock_pypi(pkg.name):
            src = Pypi(pkg)
            result = src.versions

        self.assertIsNotNone(result)
