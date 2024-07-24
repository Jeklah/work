#!/usr/bin/env python3
"""\
An interactive companion Tool used for maintaining the Golden Master for the test_standard_crc.py test.

Features:
    * Adding standards to golden master.
    * Updating the golden master
    * Check CRC for a given standard against golden master.

Usage:
    generate_standards_sheet.py <generator_hostname> [<analyser_hostname>]
    generate_standards_sheet.py --version
    generate_standards_sheet.py --help

Arguments:
    <generator_hostname>    Hostname of the Qx (e.g. qx-020123.phabrix.local) to generate signal
    <analyser_hostname>     Hostname of the Qx (e.g. qx-020123.phabrix.local) to analyse signal - generator hostname is
                            used if this is not supplied.

Options:
    -h, --help              Usage help
    --version               Show version and exit
"""

import enum
import json
import logging
import sys
import time

import click
from docopt import docopt
import pandas as pd

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

from autolib.factory import make_qx
from autolib.models.qxseries import qx
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.input_output import SDIIOType
from autolib.logconfig import autolib_log
from autolib.models.qxseries.analyser import AnalyserException
from autolib.models.qxseries.generator import GeneratorException


# Set up logging
log = logging.getLogger(autolib_log)


def generator_qx(gen_qx_hostname: str) -> qx:
    """
    Basic generator_qx setup.

    * Bouncing Box set to False
    * Output copy set to False
    * Output source set to BNC
    * SDI Outputs set to generator

    :param gen_qx_hostname: Either the hostname or IPv4 address of a Qx series device
    """
    gen_qx = make_qx(gen_qx_hostname)
    if gen_qx.query_capability(OperationMode.IP_2110):
        print(f"Generator unit {gen_qx_hostname} is in ST2110 mode, please switch mode to SDI. Exiting.")
        exit(1)

    gen_qx.generator.bouncing_box = False
    gen_qx.generator.output_copy = False
    gen_qx.io.sdi_output_source = SDIIOType.BNC
    gen_qx.io.set_sdi_outputs(("generator", "generator", "generator", "generator"))
    log.info(f"Standard Verification Generator {gen_qx.hostname} setup complete.")
    return gen_qx


def analyser_qx(analyser_qx_hostname: str) -> qx:
    """
    Basic analyse_qx setup

    * Output/input(?) source set to BNC

    :param analyser_qx_hostname: Either the hostname or IPv4 address of a Qx series device
    """
    analyse_qx = make_qx(analyser_qx_hostname)
    if analyse_qx.query_capability(OperationMode.IP_2110):
        print(f"Analyser unit {analyser_qx_hostname} is in ST2110 mode, please switch mode to SDI. Exiting.")
        exit(1)

    analyse_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f"Standard Verification Analyser {analyse_qx.hostname} setup complete.")
    return analyse_qx


def welcome():
    """
    Welcome message for the user.
    """
    click.secho('Welcome to the CRC Standard Checker tool.', bg='green', fg='black', bold=True)


def menu() -> int:
    """
    Presents the user with a menu, listing the choice of actions the user would like
    to take.

    Using click.prompt checks for values outside the given range and
    asks the user to re-enter a valid input if invalid input is given.
    """

    actions = [
                'Generate CRC Records',
                'Exit'
               ]

    print('Please choose what you would like to do from the list below.')
    for choice in actions:
        print(f'{actions.index(choice)+1}: {choice}')
    user_choice_num = click.prompt('Please select your choice using the numbers: ', type=click.IntRange(1, len(actions)))
    print()

    if user_choice_num == 2:
        exit(0)

    return user_choice_num


@enum.unique
class StandardsSubset(enum.Enum):
    NIGHTLY = "nightly"
    SINGLE = "single"
    TEST = "test"
    FAST = "fast"
    CONFIDENCE = "confidence_test_standards"
    ALL = "all"


def gen_std_list(gen_qx: qx, stds: StandardsSubset = StandardsSubset.NIGHTLY) -> list:
    """
    This is to give the companion the same filters that are used as global fixtures
    in our pytest setup, as well as the decided nightly subset.

    :param gen_qx: The Qx used to generate a list of generatable standards
    :param stds: The name of the class of standards to obtain

    :return: List of standards tuples to process
    """
    standards_list = []
    try:
        if not gen_qx.query_capability(OperationMode.IP_2110):
            if stds == StandardsSubset.NIGHTLY:  # Nightly filter. Shallow but wide-ranging subset.
                standards_list = [
                                  (1.5, '1280x720p50', 'YCbCr:422:10', '1.5G_Rec.709'),
                                  (1.5, '1920x1080p23.98', 'YCbCr:422:10', '1.5G_Rec.709'),
                                  (1.5, '2048x1080p23.98', 'YCbCr:422:10', '1.5G_Rec.709'),
                                  (1.5, '3840x2160p25', 'YCbCr:422:10', 'QL_1.5G_SQ_S-Log3_Rec.2020'),
                                  (1.5, '4096x2160p25', 'YCbCr:422:10', 'QL_1.5G_SQ_Rec.709'),
                                  (1.5, '1920x1080i60', 'RGB:444:10', 'DL_1.5G_Rec.709'),
                                  (1.5, '1920x1080i50', 'RGB:444:12', 'DL_1.5G_HLG_Rec.2020'),
                                  (1.5, '1920x1080psf30', 'YCbCr:422:12', 'DL_1.5G_HLG_Rec.2020'),
                                  (1.5, '1920x1080i60', 'RGBA:4444:10', 'DL_1.5G_Rec.2020'),
                                  (1.5, '2048x1080p30', 'YCbCrA:4224:12', 'DL_1.5G_S-Log3_Rec.2020'),
                                  (1.5, '1920x1080i60', 'YCbCrA:4444:10', 'DL_1.5G_Rec.2020'),
                                  (1.5, '4096x2160p30', 'YCbCr:422:10', 'QL_1.5G_SQ_PQ_Rec.2020'),
                                  (1.5, '1920x1080p25', 'YCbCr:422:10', '1.5G_S-Log3_Rec.2020'),
                                  ]
            elif stds == StandardsSubset.SINGLE:  # Returns smaller subset than 'fast', quicker testing.
                standards_list = [(1.5, '1920x1080p25', 'YCbCr:422:10', '1.5G_Rec.709'), ]
            elif stds == StandardsSubset.TEST:  # Returns smaller subset than 'fast', quicker testing.
                standards_list = gen_qx.generator.get_matching_standards(
                    [1.5], r"1920.*", r"YCbCr:422:10", r".*709"
                )
            elif stds == StandardsSubset.FAST:  # This filter was added to speed up testing and dev.
                standards_list = gen_qx.generator.get_matching_standards(
                    [1.5, 3.0], r"(1920x1080|1280x720)[i|p]50", "YCbCr:422:10", ".*Rec.709"
                )
            elif stds == StandardsSubset.CONFIDENCE:
                standards_list = gen_qx.generator.get_matching_standards(
                    [1.5, 3.0, 6.0, 12.0],
                    r"\d+x\d+p\d+",
                    r"YCbCr:422:10",
                    r".*709"
                )
            elif stds == StandardsSubset.ALL:
                all_stds = gen_qx.generator.get_standards()
                standards_list = [
                    [data_rate, resolution, colour_map, gamut]
                    for data_rate in all_stds
                    for resolution in all_stds[data_rate]
                    for colour_map in all_stds[data_rate][resolution]
                    for gamut in all_stds[data_rate][resolution][colour_map]
                ]
        else:
            print(f"{gen_qx.hostname} is current in IP 2110 mode. Please switch to SDI mode.")
    except NameError as exc:
        print(f'{gen_qx.hostname} could not match standard list {stds}: {exc}. Please check value of stds.')
    return standards_list


def generate_crc_record_file(gen_qx: qx, analyse_qx: qx, standards_list: list, file_path: str) -> str:
    """
    Method that enumerates through a list of standards and generates and writes the crcRecord_file dataframe for a
    given standard.

    :param gen_qx: The Qx/QxL used to generate the signal
    :param analyse_qx: The Qx/QxL used to analyse the signal (may be the same unit with loopback)
    :param standards_list: List of standards tuples
    :param file_path: An absolute or relative path and filename to write to (JSON)
    :return: Posix filename and path to generated file
    """
    qx_crcs = []

    try:
        for std in standards_list:
            _, resolution, mapping, gamut = std

            for pattern in gen_qx.generator.get_test_patterns(std[1], std[2], std[3]):
                gen_qx.generator.set_generator(resolution, mapping, gamut, pattern)
                time.sleep(3)
                crc_count = len(analyse_qx.analyser.get_crc_analyser())
                qx_settled = analyse_qx.generator.is_generating_standard(resolution, mapping, gamut, pattern)

                while qx_settled is False:
                    qx_settled = analyse_qx.generator.is_generating_standard(resolution, mapping, gamut, pattern)
                    time.sleep(0.5)

                try:
                    for crc_value in analyse_qx.analyser.get_crc_analyser():
                        try:
                            print(f'Retrieved using {gen_qx.hostname}: {std}, {pattern}, {crc_value["activePictureCrc"].upper()}')
                            dict_to_df = {}
                            dict_to_df.update(Standard=f'{std}', Pattern=f'{pattern}', CrcValue=f'{crc_value["activePictureCrc"]}', CrcCount=f'{crc_count}')
                            qx_crcs.append(dict_to_df)
                        except KeyError as data_frame_err:
                            log.error(f"An error occurred while creating dataframe: {data_frame_err}")
                            exit(1)
                except AnalyserException as analyser_exc:
                    log.error(f"An error occurred getting the analyser status: {analyser_exc}")
                    exit(1)

    except GeneratorException as exc:
        log.error(f"An error occurred processing the standard list: {exc}")
        exit(1)

    try:
        qx_dataframe = pd.DataFrame(qx_crcs)
        return write_json(gen_qx, qx_dataframe, file_path)
    except KeyError as jsonErr:
        log.error(f"An error occurred while writing JSON: {jsonErr}")
        exit(1)


def write_json(gen_qx: qx, dataframe: pd.DataFrame, file_path: str) -> str:
    """
    Serialises the dataframe to JSON for storage.

    :param gen_qx: The Qx used to generate the data in the dataframe
    :param dataframe: Pandas dataframe to serialise to JSON
    :param file_path: An absolute or relative path and filename to write to (JSON)
    :return: File and path name string
    """
    crc_meta = {}
    for key, value in zip(gen_qx.about.keys(), gen_qx.about.values()):
        crc_meta[key] = value
    results = dataframe.to_json(orient='table')
    parsed_json = json.loads(results)
    parsed_json.update(crc_meta)

    with open(file_path, 'w', encoding='utf-8') as output:
        json.dump(parsed_json, output, ensure_ascii=False, indent=4)

    return file_path


def main(arguments):
    """
    Entry point for the program.

    :param arguments: Arguments from docopt command line parser
    """
    generator_hostname = arguments.get("<generator_hostname>", None)
    analyser_hostname = arguments.get("<analyser_hostname>", None)
    if not analyser_hostname:
        analyser_hostname = generator_hostname

    gen_qx = generator_qx(generator_hostname)
    analyse_qx = analyser_qx(analyser_hostname)

    welcome()
    user_action = menu()

    if user_action == 1:
        print('Generating CRC Records...')
        print('This may take some time.\n')
        standards_list = gen_std_list(gen_qx)

        version = f'{gen_qx.about["Software_version"]}-{gen_qx.about["Build_number"]}'
        file_path = f'./crc_data/crcRecord-{StandardsSubset.NIGHTLY.value}-{version}.json'

        generate_crc_record_file(gen_qx, analyse_qx, standards_list, file_path)


if __name__ == "__main__":
    docopt_arguments = docopt(__doc__, version='1.0.0')
    main(docopt_arguments)
