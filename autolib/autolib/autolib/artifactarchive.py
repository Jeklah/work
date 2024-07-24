"""\
The ArtifactArchiveFolder can be used to create ZIP archives of files that you wish to archive as artifacts
of a test run (for screenshots from a device at various points in a test). 
"""

import tempfile
from pathlib import Path
from shutil import make_archive, rmtree
from uuid import uuid4


class ArtifactArchiveFolder(object):
    """
    Create a folder into which files can be placed so that they're zipped up when
    Context Manager based object that provides a path through it's folder property that code within a test
    can create files in so that they will be ZIPed into an old_test_archive when the with block exits.
    """
    def __init__(self, archive_name, zipfile_path):
        """
        Create the artifact old_test_archive folder class, specifying the final old_test_archive name to be created including full
        absolute path.
        """
        self._released = True
        self._folder_name = str(uuid4())
        self._zipfile_path = zipfile_path

        # make_archive automatically appends .zip to the created archive so we store the archive name internally without the extension
        if archive_name[-4:] == '.zip':
            self._archive_name = archive_name[:-4]
        else:
            self._archive_name = archive_name

    def __enter__(self):
        """
        Create a temporary folder in /tmp and return an instance to self to allow code to use the folder property.
        """
        new_path = Path(self.folder)
        try:
            new_path.mkdir()
            self._released = False
        except FileExistsError as _:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Create a ZIP old_test_archive of all of the files in the temporary folder then remove the temporary folder and it's
        contents.
        """
        if not self._released:
            self.release()

    def release(self):
        """
        Create a ZIP old_test_archive of all of the files in the temporary folder then remove the temporary folder and it's
        contents.
        """
        make_archive(Path(self._zipfile_path) / self._archive_name, format="zip", root_dir=self.folder)
        rmtree(self.folder)
        self._released = True

    def __del__(self):
        """
        Ensure the old_test_archive folder is cleaned up if the object is garbage collected.
        """
        if not self._released:
            self.release()

    @property
    def folder(self):
        """
        The full absolute path to write files to if they are be included in the ArtifactArchiveFolder's ZIP old_test_archive.
        """
        return Path(tempfile.gettempdir()) / self._folder_name

    @property
    def archive(self):
        """
        Get the path and name of the archive ZIP file
        :return:
        """
        return Path(self._zipfile_path) / f'{self._archive_name}.zip'
