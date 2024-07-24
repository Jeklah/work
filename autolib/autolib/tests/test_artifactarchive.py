import os
import zipfile

from pathlib import Path
from autolib.factory import make_artifact_archive
from autolib.artifactarchive import ArtifactArchiveFolder


def test_archive_factory_basic():
    """\
    """
    zip_archive = make_artifact_archive('monkey', Path.home())
    with zip_archive as target:
        with open(Path(target.folder) / 'random.bin', 'wb') as datafile:
            datafile.write(os.urandom(1000000))

    with zipfile.ZipFile(zip_archive.archive, "r") as archive_zip_file:
        assert 'random.bin' in archive_zip_file.namelist()

    os.unlink(zip_archive.archive)


def test_archive():
    """\
    """
    zip_archive = ArtifactArchiveFolder('moose', Path.home())
    with zip_archive as target:
        with open(Path(target.folder) / 'random.bin', 'wb') as datafile:
            datafile.write(os.urandom(1000000))

    with zipfile.ZipFile(zip_archive.archive, "r") as archive_zip_file:
        assert 'random.bin' in archive_zip_file.namelist()

    os.unlink(zip_archive.archive)
