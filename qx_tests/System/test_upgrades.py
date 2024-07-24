"""
Tests that validate upgrade and downgrade of the system software and FPGA firmware. 
"""

from datetime import datetime
import json
import logging
import os
import tempfile
import urllib
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import pytest

from autolib.factory import make_qx
from autolib.logconfig import autolib_log
from autolib.testexception import TestException

log = logging.getLogger(autolib_log)


@pytest.fixture(scope='module')
def qx(test_qx_hostname):
    """
    Pytest fixture that will create a Qx object using the test_qx_hostname global fixture.
    """
    qx = make_qx(test_qx_hostname)
    log.info(f"FIXTURE: Qx {qx.hostname} setup complete")
    yield qx
    log.info(f"FIXTURE: Qx {qx.hostname} teardown complete")


@pytest.fixture(scope='module')
def latest_software():
    """
    Obtain the build of software to upgrade to. If the environment variable LATEST_SOFTWARE_URL is set to an URL
    pointing to a phab_qx_upgrade.bin file, this will be used (allowing this test to be configured at build time
    in Jenkins) else the latest successful build from the Jenkins Gitlab Qx Linux Release Branch Build job will be used
    which is the latest build from any release_staging_* branch.
    
    We're going to test using the latest build from the release branch builder. We'll cache the file though
    to make sure that the build at the url doesn't get updated halfway through the test. The temporary file will be
    automatically removed once the fixture is torn down.
    """
    latest_software_url = os.environ.get('LATEST_SOFTWARE_URL', None)

    if not latest_software_url:
        raise TestException("LATEST_SOFTWARE_URL environment variable is not set, cannot continue.")

    with tempfile.TemporaryDirectory() as temp_dir:
        filename = Path(urlparse(latest_software_url).path).name
        downloaded_file, _ = urllib.request.urlretrieve(latest_software_url, f"{temp_dir}/{filename}")
        yield Path(downloaded_file).as_posix()


def software_releases(software_release_json_url):
    """
    Returns a dictionary created from a specified URL pointing to a json list of releases.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        filename = Path(urlparse(software_release_json_url).path).name
        downloaded_file, _ = urllib.request.urlretrieve(software_release_json_url, f"{temp_dir}/{filename}")
        with open(Path(downloaded_file).as_posix(), "rt") as json_file:
            releases = json.loads(json_file.read())
            return releases


@pytest.mark.slow
@pytest.mark.system
@pytest.mark.parametrize("test_release", software_releases("http://titan/Qx/releases.json"), ids=lambda args: f"{args.get('version',None)}->latest")
def test_upgrades(qx, test_release, latest_software):
    """
    Prove that the latest software can be installed successfully against a selection of publically released software
    upgrade packages. Given a list of software releases, install each in turn followed each time by an upgrade to the 
    latest software.
    
    Install versions specified in the file pointed to by http://titan/Qx/releases.json.
    """
    _test_upgrades(qx, test_release, latest_software)


@pytest.mark.system
@pytest.mark.parametrize("test_release", software_releases("http://titan/Qx/smoke_test_releases.json"), ids=lambda args: f"{args.get('version',None)}->latest")
def test_upgrade_basic(qx, test_release, latest_software):
    """
    Smoke test installation test. Prove that the latest software can be installed successfully against a small 
    selection of publically released software upgrade packages. Given a list of software releases, install each in 
    turn followed each time by an upgrade to the latest software.
    
    Install versions specified in the file pointed to by http://titan/Qx/smoke_test_releases.json.
    """
    _test_upgrades(qx, test_release, latest_software)


def _test_upgrades(qx, test_release, latest_software):
    """
    Prove that upgrading to the latest build from previous released versions works.

    Install released versions of the Qx software then upgrade to the latest build on Jenkins on the release branch
    job. This test takes a long time to execute (and will increase over time as we add new releases to check against.
    """
    expected_version = test_release.get('version', None)
    url = test_release.get('url', None)
    support_list = test_release.get('supports', None)
    enabled = test_release.get('enabled', False)

    # If the target device is unreachable we can shortcut the test here as block_until_ready() will
    # raise a QxException if the unit isn't ping-able within the specified ping count and delay
    # If we don't do this, we have to wait for the call to block_until_ready() made in the upgrade()
    # method to time out which takes 25 minutes (as it's waiting after the upgrade file was uploaded
    # for the upload to complete).
    qx.block_until_ready(ping_count=3, ping_delay=5)

    if type(qx).__name__ in support_list and enabled:
        # Install a released build of software from the archives
        time_start = datetime.now()
        log.info(f'Installing released build {expected_version} started at {time_start}')
        qx.upgrade(url=urllib.parse.quote(url).replace('%3A', ':'))
        time_end = datetime.now()
        log.info(f'Downgrade complete at {time_end}, upgrade took{time_end - time_start}')
        assert qx.about.get("Software_version", None) == expected_version
        log.info(f'About box reads: {qx.about}')

        # Upgrade to the latest release branch build
        time_start = datetime.now()
        log.info(f'Installing latest develop build started at {time_start}')
        qx.upgrade(file=latest_software, force_name=True)
        time_end = datetime.now()
        log.info(f'Upgrade complete at {time_end}, upgrade took{time_end - time_start}')
        log.info(f'About box reads: {qx.about}')
    else:
        pytest.skip(f"Skipping test - release {expected_version} {'is not supported on this device' if enabled else 'is not enabled'}")
