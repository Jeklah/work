import datetime
import inspect
import requests
from pathlib import Path
from typing import Union

from autolib.models.blackmagic.hyperdeck import HyperDeckStudio
from autolib.models.qxseries.qx import Qx
from autolib.models.qxseries.qxl import QxL
from autolib.models.qxseries.qxp import QxP

from autolib.artifactarchive import ArtifactArchiveFolder


def make_qx(hostname: str, http_session: Union[requests.Session, None] = None):
    """
    Create a Qx or QxL instance, the type will be determined by the response to the system/about Rest API call.
    """
    qx = Qx(hostname, http_session)
    details = qx.about
    if details['device'] == "QxL":
        return QxL(hostname, http_session)
    elif details['device'] == "QxP":
        return QxP(hostname, http_session)
    else:
        return qx


def make_hyperdeck(*args, **kwargs):
    """
    Create a HyperDeckStudio instance. As the HyperDeckStudio class is subclassed to provide support for model specific
    features, this will be extended to return an appropriate object instance.
    """
    return HyperDeckStudio(*args, **kwargs)


def make_artifact_archive(artifact_id=None, zipfile_path=Path.home()):
    """
    Return an instance of an ArtifactArchiveFolder where the old_test_archive name is the calling method / function
    name followed by a date / time stamp (ISO format)
    """

    timestamp = datetime.datetime.now().strftime("%d%m%y-%H%M%S")

    if artifact_id is None:
        module_name = inspect.getmodulename(inspect.stack()[1][1])
        function_name = inspect.stack()[1][3]
        archive_name = f'{module_name}_{function_name}_{timestamp}.zip'
    else:
        archive_name = f'{artifact_id}_{timestamp}.zip'

    return ArtifactArchiveFolder(archive_name, zipfile_path)
