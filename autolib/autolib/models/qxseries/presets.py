"""\
Provides classes for interacting with presets on the Qx family of devices.
"""

import json
import os
import tempfile
import time
import logging
import requests
from urllib.parse import quote

from autolib.models.qxseries.qxexception import QxException
from autolib.ssh import SSHTools

from autolib.models.qxseries.api_wrapper import APIWrapperBase
from autolib.models.qxseries.session import DEFAULT_SESSION


class PresetManager(APIWrapperBase,
                    url_properties={
                        "user_presets": {"GET": "presets/userPresets",
                                         "POST": "presets/userPresets",
                                         "DOC": "Get a list of presets or create a new preset"},
                    },
                    url_methods={
                        "user_preset": {
                            "GET": ("presets/userPresets/{preset_name}",
                                    "Get file details for a named preset."),
                            "PUT": ("presets/userPresets/{preset_name}",
                                    "Update a named preset with the current settings or load the named preset."),
                            "POST": ("presets/userPresets",
                                     "Create a new preset with the current settings."),
                            "DELETE": ("presets/userPresets/{preset_name}",
                                       "Delete a named preset.")
                        },
                    },
                    http_session=DEFAULT_SESSION
                    ):
    """
    Get and set input/output settings on devices supporting the Qx REST API.
    """

    def __init__(self, base_url: str, logger: logging.Logger, hostname: str, http_session: requests.Session):
        super().__init__(logger, hostname)
        self._meta_initialise(base_url, http_session)
        self._ssh = SSHTools(logger, hostname)

    def rename(self, preset_name: str, new_name: str):
        """
        Rename a preset on the device to the new name specified
        :param preset_name: Remove name of the preset to rename
        :param new_name: The name to change it to
        """
        self.put_user_preset(preset_name, {"action": "rename", "newPresetName": new_name})

    def load(self, preset_name: str):
        """
        Load a preset on the device
        :param preset_name: Remove name of the preset to rename
        """
        self.put_user_preset(preset_name, {"action": "load"})

    def delete(self, preset_name):
        """
        Delete a preset on the device
        :param preset_name: Remove name of the preset to rename
        """
        self.delete_user_preset(preset_name)

    def list(self) -> list:
        """
        Obtain a list of the presets on the device.
        """
        data = self.user_presets
        return [x['rel'] for x in data.get('links', None) if x.get('rel', None) not in ['self', None]]

    def create(self, preset_name: str) -> str:
        """
        Create a preset with the specified name.
        :param preset_name: Name for the preset
        :return: Preset filename
        """
        preset_response = self.post_user_preset({})
        self.rename(quote(quote(preset_response['presetName'])), preset_name)   # @DUNC Why must we double quote?
        return f"{preset_name}"

    def upload(self, preset_file_path: str, preset_name: str):
        """
        Upload a preset file to the device with the specified preset_name.
        :param preset_file_path: File path / name of the JSON preset file.
        :param preset_name: Name of the preset on the device when uploaded
        """
        with tempfile.NamedTemporaryFile(mode="w+t", delete=False) as modified_preset:
            with open(preset_file_path, "r") as preset_file:
                modified_preset_json = json.load(preset_file)
                modified_preset_json["Name"] = preset_name
                modified_preset.write(json.dumps(modified_preset_json))
                modified_preset.flush()

        self._ssh.upload_via_sftp(modified_preset.name, f"/transfer/presets/{preset_name}.preset")
        os.remove(modified_preset.name)

        for retry in range(10):
            time.sleep(2)
            # Request a refresh of available presets
            if preset_name in self.list():
                return

        raise QxException(f"Uploaded preset {preset_name} does not appear to be available on the unit due to an unknown failure.")

    def download(self, preset_name, local_filename):
        """
        Download a preset by name to a local filename.
        :param preset_name: Name of the preset on the device
        :param local_filename: File path / name to download the preset to.
        """
        return self._ssh.download_via_sftp(f"/transfer/presets/{preset_name}.preset", local_filename)
