import setuptools
import os

# The version number of the installable package is set here. The format used in 
# setuptools packages is fully described in PEP 440 (https://www.python.org/dev/peps/pep-0440/)
# but to summarise, it must be of the form:
#
#     [N!]N(.N)*[{a|b|rc}N][.postN][.devN]
#
# The only octets we should set here are the first three (e.g. 1.0.4). We will NOT append 'a',
# 'b' or 'rc' to this on the master branch under any circumstances.
# Setuptools does not enforce meaning to the main version number so we will adhere to the rules
# set out by Semantic Versioning (semver.org). Here is a summary:
#
#     Given a version number MAJOR.MINOR.PATCH, increment the:
#     
#         MAJOR version when you make incompatible API changes,
#         MINOR version when you add functionality in a backwards compatible manner, and
#         PATCH version when you make backwards compatible bug fixes.
#     
# The build number will come from the CI pipeline and will be appended automatically. If there
# is a problem importing the CI generated ci_generated.py, the package will be built with
# a version number 0.0.0.dev0. It is not expected that the CI system should upload this to
# any package index.

AUTOLIB_VERSION = '0.9.9'
build_number = os.getenv('BUILD_NUMBER')

# The build number from CI will be set as an environment variable. If it's not set then
# we assume that there's a problem or the build is a local test build. In these cases
# the package version string will be set to 0.0.0.dev0

if build_number:
    package_version = f'{AUTOLIB_VERSION}.{build_number}'
else:
    package_version = '0.0.0.dev0'

pkg_root = os.path.dirname(os.path.realpath(__file__))

with open(f'{pkg_root}/README.md', 'r') as readme:
    long_description = readme.read()

with open(f'{pkg_root}/requirements.txt', 'r') as requirements:
    reqs = requirements.readlines()

setup_py = f"""\
import setuptools
import os

setuptools.setup(
    name='phabrix_autolib',
    version='{package_version}',
    author='Duncan Webb',
    author_email='duncan.webb@phabrix.com',
    packages=setuptools.find_packages(),
    scripts=['autolib/utils/generate_standards_sheet.py', 'autolib/utils/take_screenshot.py',
             'autolib/utils/plot_jitter_responses.py', 'autolib/utils/upgrade_qx_family.py'],
    url='http://phabrix.com',
    license='LICENSE.txt',
    description='Phabrix in-house automation library',
    long_description='''{long_description}''',
    long_description_content_type='text/markdown',
    install_requires={reqs}
)
"""

print(setup_py)
