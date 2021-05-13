"""
Script to upload a directory of presets to a Qx unit.

"""

import os
import click
import logging
from pathlib import Path
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.qxexception import QxException

log = logging.getLogger(test_system_log)

def upload_preset(dirpath, host):
    """
    Upload method that goes through each file in a given directory and uploads them.
    """
    qx = make_qx(hostname=host)
    myDir = Path(dirpath)

    try:
        for file in myDir.glob('*.preset'):
            filepathname = os.path.basename(file)
            filename = os.path.splitext(filepathname)
            print(f"Uploading preset file: {filename[0]}")
            qx.preset.upload(file, filename[0])
            log.info(f"Upload complete: {filename[0]}")
    except QxException as err:
        raise QxException(f"QxException occurred during uploading presets: {err}")
        log.error(f"Error: Upload FAILED. {err}")


@click.command()
@click.argument('dirpath')
@click.option('--host', prompt='Please enter a hostname')
def main(dirpath, host):
    """
    \b
    Upload Presets script.
    \b
    :param dirPath string  Path of the directory you would like to upload presets from.
    :option --host string  Hostname of the unit you would like to upload presets to.
    :option --help         Shows this message.

    To be used from a machine that has the test_system installed.
    In the given example, presets is a folder with preset JSON files in.
    This example folder is in the same folder as this script.

    Example usage:
    python3 load_presets.py presets
    python3 load_presets.py presets --host <desired_host>

    """
    upload_preset(dirpath, host)

if __name__ == '__main__':
    main()
