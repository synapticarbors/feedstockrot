from github import Github
from github.GithubException import BadCredentialsException as GithubBadCredentialsException
from github.PaginatedList import PaginatedList
from github.AuthenticatedUser import AuthenticatedUser
from github.Organization import Organization
from .feedstockrot import FeedstockRot
import argparse
import os
import logging
from typing import List
from .package import Package


def main() -> int:

    parser = argparse.ArgumentParser(
        description='Check for outdated conda-forge packages'
    )
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    parser.add_argument(
        '--github',
        action='store_true',
        help='Use your Github repositories as a package list. Requires FEEDSTOCKROT_GITHUB_TOKEN env var'
    )
    # TODO: consider something like this:
    # parser.add_argument(
    #     '--all',
    #     action='store_true',
    #     help='Check all conda-forge packages'
    # )

    parser.add_argument(
        'packages', nargs='*', help='Additional packages to check'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.github and len(args.packages) < 1:
        # well, nothing to do here.
        return 0

    rot = FeedstockRot()

    rot.add(args.packages)
    logging.debug('Added packages from CLI')

    if args.github:
        token = os.getenv('FEEDSTOCKROT_GITHUB_TOKEN', None)
        if not token:
            logging.error('No Github token found')
            return 1

        gh = Github(token)

        try:
            gh_user = gh.get_user()  # type: AuthenticatedUser
            logging.debug('Authenticated to GitHub as: {}'.format(gh_user.name))
        except GithubBadCredentialsException:
            logging.error('Authentication to GitHub failed')
            return 1
        print("Authenticated to GitHub")

        gh_repos = gh_user.get_repos()  # type: PaginatedList
        logging.debug('Got GitHub repositories reference')

        gh_repos = filter(lambda repo: repo.permissions.push, gh_repos)
        logging.debug('Filter repos by push access')

        rot.add_repositories(gh_repos)
        logging.debug('Added repos as packages')

    up_to_date = []  # type: List[Package]
    unknown = []  # type: List[Package]
    upgradeable = []  # type: List[Package]
    not_found = []  # type: List[Package]

    if len(rot.packages) < 1:
        print("No packages")
        return 0

    for pkg in rot.packages:
        if not pkg.latest_feedstock_version:
            not_found.append(pkg)
        elif pkg.latest_external_upgradeable_version:
            upgradeable.append(pkg)
        elif not pkg.latest_external_version:
            unknown.append(pkg)
        else:
            up_to_date.append(pkg)

    if len(up_to_date):
        print("Up-to-date:")
        for pkg in up_to_date:
            print("- {}".format(pkg.name))
    if len(unknown):
        print("Unknown (check these manually):")
        for pkg in unknown:
            print("- {}: {}".format(pkg.name, pkg.latest_feedstock_version))
    if len(upgradeable):
        print("Upgradeable:")
        for pkg in upgradeable:
            # TODO: print out source name if different
            print("- {}: {} -> {}".format(
                pkg.name, pkg.latest_feedstock_version, pkg.latest_external_upgradeable_version))
    if len(not_found):
        print("Not found (no feedstock found, check for typos):")
        for pkg in not_found:
            print("- {}".format(pkg.name))

    return 0


def main_run():
    import sys
    sys.exit(main())


if __name__ == '__main__':
    main_run()
