from .source import Source, PackageInfo
from typing import Set, List, Dict
import requests
import yaml
import jinja2


# From https://github.com/conda-forge/conda-smithy/blob/master/conda_smithy/lint_recipe.py#L19
# Allows recipes to be parsed even with undefined jinja2 variables
class Jinja2NullUndefined(jinja2.Undefined):
    def __unicode__(self):
        return str(self._undefined_name)

    def __getattr__(self, name):
        return str('{}.{}'.format(self, name))

    def __getitem__(self, name):
        return '{}["{}"]'.format(self, name)


class Condaforge(Source):

    _DEFAULT_OWNER = 'conda-forge'
    _DEFAULT_PLATFORMS = ['linux-64', 'osx-64', 'win-64']
    _DEFAULT_REPODATA_URL = 'https://conda.anaconda.org/{}/{}/repodata.json'
    _DEFAULT_RECIPE_URL = 'https://raw.githubusercontent.com/conda-forge/{}-feedstock/master/recipe/meta.yaml'

    _repodata = {}

    @classmethod
    def _possible_names(cls, package: PackageInfo):
        name = package.get_name()
        names = list(super()._possible_names(package))
        if name.endswith('-feedstock'):
            names.append(name[:-len('-feedstock')])
        return names

    @classmethod
    def _get_repodata(cls, platform) -> Dict:
        """
        {
            "packages": {
                "$package_name": {
                    "name": "",
                    "version": "",
                    ...
                }
            }
        }
        """
        if platform not in cls._repodata:
            url = cls._DEFAULT_REPODATA_URL.format(cls._DEFAULT_OWNER, platform)
            response = requests.get(url)
            if response.status_code != 200:
                return None

            cls._repodata[platform] = response.json()
        return cls._repodata[platform]

    @classmethod
    def _get_repodata_packages_aggregate(cls) -> List[Dict]:
        packages = []
        for platform in cls._DEFAULT_PLATFORMS:
            repodata = cls._get_repodata(platform)
            if repodata is None:
                continue

            platform_packages = repodata['packages'].values()
            packages += platform_packages
        return packages

    @classmethod
    def _fetch_versions(cls, name: str) -> Set[str]:
        versions = set()
        for package in cls._get_repodata_packages_aggregate():
            if package['name'] == name:
                versions.add(package['version'])
        return versions if len(versions) > 0 else None

    def _get_recipe(self) -> Dict:
        resp = requests.get(self._DEFAULT_RECIPE_URL.format(self.name))
        if resp.status_code != 200:
            return None

        # conda-forge recipes commonly use jinja2 for variables
        try:
            parsed = jinja2.Template(resp.text, undefined=Jinja2NullUndefined)
            rendered = parsed.render()
            return yaml.load(rendered)
        except (jinja2.TemplateError, yaml.YAMLError):
            return None

    def get_recipe_urls(self) -> List[str]:
        """
        Get URLs for a feedstock that may be useful for discerning project info/versions from other sources
        """
        recipe = self._get_recipe()
        urls = []

        if recipe is None:
            return urls

        if 'about' in recipe and 'home' in recipe['about']:
            urls.append(recipe['about']['home'])
        if 'source' in recipe:
            if 'url' in recipe['source']:
                urls.append(recipe['source']['url'])
            if 'git_url' in recipe['source']:
                urls.append(recipe['source']['git_url'])

        return urls
