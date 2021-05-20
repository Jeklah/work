"""
Script to help automate the uploading of a directory of presets to a Qx or QxL and possibly removing the
old presets ready for production presets to be put on after testing.
Able to iterate number of sub-dirs in a directory and generate a menu with options for the user
to pick which sub-dir they would like to upload presets from.

"""

import os
import click
import logging
from pathlib import Path
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.qxexception import QxException

log = logging.getLogger(test_system_log)
presetDirs = []

def menu():
    """
    Displays welcome message and iterates over folders in the current working directory to
    generate a menu for the user to choose where to upload preset files from.

    This method should be split up into two seperate methods, one as a welcome message for the user,
    another for making and printing the list. This way, when the user selects the --just-delete option, it
    would be possible not to display the menu, as they don't need to see it while using this option.
    """
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
    qx.request_capability(OperationMode.SDI)
    myDir = Path(presetDirName)

    try:
        for file in myDir.glob('*.preset'):
            filePathName = os.path.basename(file)
            filename = os.path.splitext(filePathName)
            print(f"Uploading preset file: {filename[0]}")
            qx.preset.upload(file, filename[0])
            log.info(f"Upload complete: {filename[0]}")
    except QxException as err:
        log.error(f"Error: Upload FAILED. {err}")
        raise QxException(f"QxException occurred during uploading presets: {err}")


def delete_preset(host):
    """
    Delete all presets on the unit after a confirmation check.

    :param host string
    """
    qx = make_qx(hostname=host)
    qx.request_capability(OperationMode.SDI)
    delPresets = qx.preset.list()

    for preset in delPresets:
        click.echo(f'Deleting preset file: {preset}')
        qx.preset.delete(preset)


@click.command()
@click.option('--just-delete', '-jd', help='Just delete presets on the Qx/QxL', flag_value='justDelete', is_flag=True)
@click.option('--delete', '-d', help='Delete the presets on the Qx/QxL before uploading.', is_flag=True)
@click.option('--host', '-h', help='Hostname of the unit.', prompt='Please enter a hostname.')
def main(host, delete, just_delete):
    """
    \b
    Upload Presets script, with option to delete any presets currently on the Qx/QxL.
    \b
    :option --delete      Use this flag if you would like to delete presets before uploading.
    :option --just-delete Use this flag if you would like to just delete presets without uploading new ones.
    :option --host string Hostname of the unit you would like to upload presets to.
    :option --help        Shows this message.
    \b
    To be used from a machine that has the test_system installed.
    In the given example, presets is a folder with preset JSON files in.
    This example folder is in the same folder as this script.
    \b
    Example usage:
    \b
    python3 load_presets.py
    python3 load_presets.py --host <desired_host>
    python3 load_presets.py --host <desired_host> --delete
    python3 load_presets.py --host <desired_host> --just-delete
    python3 load_presets.py --delete
    python3 load_presets.py --just-delete
    python3 load_presets,py --help
    """
    exitFlag = False
    dirPath = menu()

    if just_delete:
        delete_preset(host)
        exit()

    if delete:
        while not exitFlag:
            print('Are you sure you want to delete the presets on this machine?')
            ans = click.getchar()

            if ans == 'y' or ans == 'Y':
                delete_preset(host)
                upload_preset(dirPath, host)
                exitFlag = True

            elif ans == 'n' or ans == 'N':
                print('Aborting!')
                exit()

            else:
                print('Invalid input entered. Please choose either [Y/n].')
    else:
        upload_preset(dirPath, host)
        exit()

if __name__ == '__main__':
    main()
