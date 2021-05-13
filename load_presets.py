"""
Script to help automate the uploading of a directory of presets to a Qx or QxL and possibly removing the
old presets ready for production presets to be put on after testing.

"""

import os
import click
import logging
from pathlib import Path
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.qxexception import QxException

log = logging.getLogger(test_system_log)
presetDirs = []

def menu():
    click.secho('Welcome to the Preset Loader.', bg='green', fg='black', bold=True)
    print()

    print('Please choose the directory you would like to upload presets from.')
    pwd = os.getcwd()
    for subdir in os.listdir(pwd):
        if os.path.isdir(subdir):
            presetDirs.append(os.path.basename(subdir))
            click.echo(click.style('* ', fg='blue', bold=True) + str(presetDirs.index(os.path.basename(subdir))+1) + ' ' + os.path.basename(subdir))
    print()
    presetChoiceNum = click.prompt('Directory Choice: ', type=click.IntRange(1, len(presetDirs)))
    presetDirName = presetDirs[int(presetChoiceNum-1)]

    print(f'You chose: {presetDirName}')

    return presetDirName

def upload_preset(presetDirName, host):
    """
    Upload method that goes through each file in a given directory and uploads them.

    :param presetDirName string
    :param host string
    """
    qx = make_qx(hostname=host)
    myDir = Path(presetDirName)

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

#@click.command()
#@click.confirmation_option(prompt='Are you sure you want to delete all the presets currently on the unit?')
def delete_preset(host):
    """
    Delete all presets on the unit after a confirmation check.

    :param host string
    """
    qx = make_qx(hostname=host)
    delPresets = qx.preset.list()
    for lst in delPresets:
        qx.preset.delete(lst)


@click.command()
@click.option('--delete', help='Delete the presets on the Qx/QxL before uploading.', is_flag=True)
@click.option('--host', help='Hostname of the unit.', prompt='Please enter a hostname.')
def main(host, delete):
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
    dirPath = menu()
    if(delete):
        print('are you sure you want to delete')
        ans = click.getchar()
        if ans == 'y' or ans == 'Y':
            delete_preset(host)
            upload_preset(dirPath, host)
        elif ans == 'n' or ans == 'N':
            print('Aborting!')
            exit()
    else:
        upload_preset(dirPath, host)

if __name__ == '__main__':
    main()
