"""
Tests that concern NMOS IDs to confirm that they remain unique to a device but unchanging.
"""

import json
import logging
import os
import tempfile
import urllib
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from pprint import pformat

import pytest

from autolib.factory import make_qx
from autolib.models.qxseries.operationmode import OperationMode
from autolib.logconfig import autolib_log

log = logging.getLogger(autolib_log)


@pytest.fixture(scope='module')
def qx(test_qx_hostname):
    """
    Pytest fixture that will create a Qx object using the test_qx_hostname global fixture.
    """
    qx = make_qx(test_qx_hostname)
    qx.request_capability(OperationMode.IP_2110)
    old_nmos_mode = qx.nmos.enabled
    qx.nmos.enable()
    yield qx
    if not old_nmos_mode:
        qx.nmos.disable()


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
    latest_software_url = os.environ.get('LATEST_SOFTWARE_URL', "http://jenkins:8080/job/GitLab%20Qx%20Linux%20Release%20Branch%20Build/lastSuccessfulBuild/artifact/sw/phab_qx_upgrade.bin")

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
            return [release for release in releases if release['version'] in ('4.3.0', )]


def get_nmos_ids(qx):
    """\
    Get a dictionary of all NMOS resource IDs for a Qx only adding keys if the resources exist
    """
    nmos_ids = dict(node=qx.nmos.node.self['id'])

    if devices := qx.nmos.node.devices:
        nmos_ids['devices'] = [dev['id'] for dev in devices]

    if sources := qx.nmos.node.sources:
        nmos_ids['sources'] = [src['id'] for src in sources]

    if flows := qx.nmos.node.flows:
        nmos_ids['flows'] = [flow['id'] for flow in flows]

    try:
        qx.nmos.dual_interface_sender = False
    except NotImplementedError:
        pass

    if senders := qx.nmos.node.senders:
        nmos_ids['single_interface_senders'] = [send['id'] for send in senders]

    try:
        qx.nmos.dual_interface_sender = True
    except NotImplementedError:
        pass

    if senders := qx.nmos.node.senders:
        nmos_ids['dual_interface_senders'] = [send['id'] for send in senders]

    qx.nmos.dual_interface_receiver = False
    if receivers := qx.nmos.node.receivers:
        nmos_ids['single_interface_receivers'] = [rcv['id'] for rcv in receivers]

    qx.nmos.dual_interface_receiver = True
    if receivers := qx.nmos.node.receivers:
        nmos_ids['dual_interface_receivers'] = [rcv['id'] for rcv in receivers]

    return nmos_ids


@pytest.mark.ip2110
@pytest.mark.parametrize("test_release", software_releases("http://titan/Qx/releases.json"), ids=lambda x: x['version'])
def test_nmos_ids_after_upgrade(qx, test_release, latest_software):
    """\
    Prove that upgrading to the latest build from a known good NMOS release does not cause the NMOS IDs to change.
    """
    expected_version = test_release.get('version', None)
    url = test_release.get('url', None)
    support_list = test_release.get('supports', None)

    if type(qx).__name__ in support_list:

        qx.upgrade(url=urllib.parse.quote(url).replace('%3A', ':'))
        assert qx.about.get("Software_version", None) == expected_version
        log.info(f'About box reads: {qx.about}')
        old_ids = get_nmos_ids(qx)

        qx.upgrade(file=latest_software, force_name=True)
        log.info(f'About box reads: {qx.about}')
        new_ids = get_nmos_ids(qx)

        log.info(f'Old NMOS IDs: {pformat(old_ids)}')
        log.info(f'New NMOS IDs: {pformat(new_ids)}')
        assert new_ids.items() >= old_ids.items()

    else:
        pytest.skip(f"Skipping test - release {expected_version} is not supported on this device")
