"""
A Companion Tool used for maintaining the Golden Master.
Features:
    * Adding standards to golden master.
    * Updating the golden master
    * Check CRC for a given standard against golden master.

Environment Variables that need to be set:
    * GENERATOR_QX
    * ANALYSER_QX
    * TEST_QX

These can be set by using the following command from a terminal:

export GENERATOR_QX='qx-<serial-number>.local'
export ANALYSER_QX='qx-<serial-number>.local'
export TEST_QX='qx-<serial-number>.local'
"""

import os
import sys
import time
import json
import click
import pickle
import logging
import pandas as pd
if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")
from test_system.factory import make_qx
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.io import SDIIOType
from test_system.logconfig import test_system_log
from test_system.models.qxseries.analyser import AnalyserException
from test_system.models.qxseries.generator import GeneratorException


# Set up logging
log = logging.getLogger(test_system_log)


# Get Env Variables
GENERATOR = os.getenv("GENERATOR_QX")
ANALYSER= os.getenv("ANALYSER_QX")
TEST = os.getenv("TEST_QX")


def generator_qx(GENERATOR):
    """
    Basic generator_qx setup.

    :parameter: GENERATOR string

    * Bouncing Box set to False
    * Output copy set to False
    * Output source set to BNC
    * SDI Outputs set to generator
    """
    gen_qx = make_qx(hostname=GENERATOR)
    gen_qx.generator.bouncing_box = False
    gen_qx.generator.output_copy = False
    gen_qx.io.sdi_output_source = SDIIOType.BNC
    gen_qx.io.set_sdi_outputs(("generator", "generator", "generator", "generator"))
    log.info(f"Standard Verification Generator {gen_qx.hostname} setup complete.")
    return gen_qx


def analyser_qx(ANALYSER):
    """
    Basic analyse_qx setup

    :parameter: ANALYSER string

    * Output/input(?) source set to BNC
    """
    analyse_qx = make_qx(hostname=ANALYSER)
    analyse_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f"Standard Verification Analyser {analyse_qx.hostname} setup complete.")
    return analyse_qx


def welcome():
    """
    Welcome message for the user.
    """
    click.secho('Welcome to the CRC Standard Checker tool.', bg='green', fg='black', bold=True)


def menu():
    """
    Presents the user with a menu, listing the choice of actions the user would like
    to take.

    Using click.prompt checks for values outside the given range and
    asks the user to re-enter a valid input if invalid input is given.
    """
    actions = [
                'Update Standard',
                'Add Standard',
                'Check Standard CRC',
                'Generate CRC Records',
                'Exit'
               ]
    print('Please choose what you would like to do from the list below.')
    for choice in actions:
        print(f'{actions.index(choice)+1}: {choice}')
    user_choice_num = click.prompt('Please select your choice using the numbers: ', type=click.IntRange(1, len(actions)))
    print()
    if user_choice_num == 5:
        print('Bye!')
        exit(0)
    print(f'You chose: {user_choice_num}: {actions[user_choice_num-1]}.')
    return user_choice_num


def user_input(user_choice_num):
    """
    Takes the input from the user and returns a list and the date the user would like to amend.

    :parameter: user_choice_num string
    :return: search_date date,
             input_std_list_file list
    """
    input_std_list_file = click.prompt('Please enter the name of the input file containing the standards, patterns and CRC values.', type=click.STRING)
    if user_choice_num == 1:
        search_date = click.prompt('Please enter the date of the records you would like to update, in the form "Sep-16-2021"', type=click.STRING)
        return search_date, input_std_list_file
    elif user_choice_num == 3:
        search_date = click.prompt('Please enter the date of the records you would like to check, in the form "Sep-16-2021"', type=click.STRING)
        return search_date, input_std_list_file


def gen_std_list(gen_qx, stds="nightly"):
    """
    This is to give the companion the same filters that are used as global fixtures
    in our pytest setup, as well as the decided nightly subset.

    :parameter: stds string default: nightly
                gen_qx object
    :return: standards_list list
             stds string
    """
    try:
        if not gen_qx.query_capability(OperationMode.IP_2110):
            if stds == "nightly": # Nightly filter. Selected standards to give us the widest/broadest coverage as possible.
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
            elif stds == "test": # Returns smaller subset than 'fast', quicker testing.
                standards_list = gen_qx.generator.get_matching_standards(
                    [1.5], r"1920.*", r"YCbCr:422:10", r".*709"
                )
            elif stds == "fast": # This filter was added to speed up testing and dev.
                standards_list = gen_qx.generator.get_matching_standards(
                    [1.5, 3.0], r"(1920x1080|1280x720)[i|p]50", "YCbCr:422:10", ".*Rec.709"
                )
            elif stds == "confidence_test_standards":
                standards_list = gen_qx.generator.get_matching_standards(
                    [1.5, 3.0, 6.0, 12.0],
                    r"\d+x\d+p\d+",
                    r"YCbCr:422:10",
                    r".*709"
                )
            elif stds == "all":
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
    except NameError as stdErr:
        print(f'{gen_qx.hostname} could not match standard list {stds}: {stdErr}. Please check value of stds.')
    return standards_list


def check_standards(gen_qx, standards_list):
    """
    Debugging method. Purely used to check the standards list.

    :parameter: gen_qx object
                standards_list list
    """
    try:
        for std in standards_list:
            print(type(std))
    except GeneratorException as std_list_err:
        log.error(f"An error occurred while reading standards_list: {std_list_err}")


def check_patterns(gen_qx, standards_list):
    """
    Debugging method. Purely used to check the pattern list.

    :parameter: gen_qx object
                standards_list list

    std[1] = resolution
    std[2] = colour mapping
    std[3] = gamut
    """
    try:
        for std in standards_list:
            test_patterns = gen_qx.generator.get_test_patterns(std[1], std[2], std[3])
        print(test_patterns)
    except GeneratorException as std_list_err:
        log.error(f"An error occurred while reading standards_list: {std_list_err}")


def get_patterns(gen_qx, std):
    """
    Retrieves all supported patterns for a given standard.

    :parameter: gen_qx object
                standards_list list

    :return: test_patterns list

    std[1] = resolution
    std[2] = colour mapping
    std[3] = gamut
    """
    try:
        test_patterns = gen_qx.generator.get_test_patterns(std[1], std[2], std[3])
        return test_patterns
    except GeneratorException as pattErr:
        log.error(f"An error occurred while getting test_patterns: {pattErr}")


def set_crc_count(gen_qx):
    """
    Gets the number of crcs for the standard and pattern that is currently being generated.

    :parameter: gen_qx object
    :return: crc_count int
    """
    crc_count = len(gen_qx.analyser.get_crc_analyser())
    return crc_count


def generate_crcRecord(gen_qx, analyse_qx, standards_list, std_filter):
    """
    Method that enumerates through a list of standards and
    generates and writes the crcRecord dataframe for a
    given standard.

    :parameter: gen_qx object,
                analyse_qx object,
                standards_list list,
                std_filter string
    """
    qx_crcs = []
    qx_settled = False
    crc_count = 0
    try:
        for std in standards_list:
            data_rate, resolution, mapping, gamut = std
            try:
                test_patterns = get_patterns(gen_qx, std)
                for pattern in test_patterns:
                    try:
                        gen_qx.generator.set_generator(resolution, mapping, gamut, pattern)
                        time.sleep(3)
                        crc_count = set_crc_count(gen_qx)
                        qx_settled = analyse_qx.generator.is_generating_standard(resolution, mapping, gamut, pattern)
                        while qx_settled is False:
                            qx_settled = analyse_qx.generator.is_generating_standard(resolution, mapping, gamut, pattern)
                        try:
                            for crc_value in analyse_qx.analyser.get_crc_analyser():
                                try:
                                    print(f'retrieved using qx: {std}, {pattern}, {crc_value["activePictureCrc"].upper()}')
                                    dict_to_df = {}
                                    dict_to_df.update(Standard=f'{std}', Pattern=f'{pattern}', CrcValue=f'{crc_value["activePictureCrc"]}', CrcCount=f'{crc_count}')
                                    qx_crcs.append(dict_to_df)
                                except KeyError as dataFrameErr:
                                    log.error(f"An error occured while creating dataframe: {dataFrameErr}")
                        except AnalyserException as getAnlyStatErr:
                            log.error(f"An error occurred getting the analyser status: {getAnlyStatErr}")
                    except GeneratorException as setStdErr:
                        log.error(f"An error occurred setting the standard: {setStdErr}")
            except GeneratorException as genErr:
                log.error(f"An error occurred generating the standard: {genErr}")
    except GeneratorException as stdErr:
        log.error(f"An error occurred processing the standard list: {stdErr}")
    try:
        qx_dataframe = pd.DataFrame(qx_crcs)
        write_dataframe(qx_dataframe, std_filter, gen_qx)
        write_json(qx_dataframe, std_filter, gen_qx)
    except KeyError as pickleErr:
        log.error(f"An error occurred while pickling: {pickleErr}")


def unpickle_crcRecord(version, std_filter):
    """
    Unpickles the pkl file and returns a pandas dataframe.

    This is to keep the code as DRY as possible.

    :parameter: version string
                std_filter string
    """
    # @Arthur fast/test/whatever should be selected and changed
    # leaving this until after walkthrough. 'confidence' needs to be changed to std-filter variable.
    unpickled_crcs = pd.read_pickle(f"./crcRecord-{std_filter}-{version}.pkl")
    return unpickled_crcs


def write_dataframe(dataframe, std_filter, gen_qx):
    """
    Writes the given dataframe to file.

    This is to keep the code as DRY as possible.

    :parameter: dataframe pandas.core.DataFrame
                std_filter string
                gen_qx object
    """
    version = gen_qx.about['Software_version']
    for key, value in zip(gen_qx.about.keys(), gen_qx.about.values()):
        dataframe.attrs[key] = value
    records = open(f"crcRecord-{std_filter}-{version}.pkl", "wb")
    pickler = pickle.Pickler(records)
    pickler.dump(dataframe)
    records.close()


def write_json(dataframe, std_filter, gen_qx):
    """
    Writes the given dataframe to a human readable format (JSON).

    :parameter: dataframe pandas.core.DataFrame
                std_filter string
                gen_qx object
    """
    crc_meta = {}
    version = gen_qx.about['Software_version']
    for key, value in zip(gen_qx.about.keys(), gen_qx.about.values()):
        crc_meta[key] = value
    results = dataframe.to_json(orient='table')
    parsed_json = json.loads(results)
    parsed_json.update(crc_meta)

    with open(f'crcRecord-{std_filter}-{version}.json', 'w', encoding='utf-8') as output:
        json.dump(parsed_json, output, ensure_ascii=False, indent=4)


def read_input_file(input_std_pattern_crc_list):
    """
    Reads the given file for input for use in 3 methods:
        * add_standard()
        * check_crc()
        * update_crc()

    This is to keep the code as DRY as possible.

    :parameter: input_std_pattern_crc_list list
    """
    with open(input_std_pattern_crc_list) as reader:
        contents = reader.read().split('\n')
    input_stds = []

    for line in contents:
        if line == '':
            continue
        input_stds.append(line.split(','))
    return input_stds


def add_standard(input_std_pattern_crc_list, crcRecord):
    """
    Adds a standard from a given list.

    While the given list may contain patterns and crc values, this is NOT how the Qx/QxL operates.
    I have doubled checked with Nik C, which he confirmed that when adding standards, we would only be
    given the standard. The Qx would then select the valid patterns for that standard, and from there
    generate the CRC values.
    We do NOT want to be storing new values other parties have given us in the golden master, only supported
    ones. For this reason, when adding a standard, only the standard value is filled in. The rest are
    populated with N/a.

    A generate_pattern_crcs() method would be a good addition for future expansion of this tool
    to allow quickly filling out the N/a information with actual values without generating the
    entire crcRecord.

    Only updating the golden master with a standard field, as the test_patterns that are relevant for that standard will
    be generated on the qx, as will the CRC values for the test patterns.

    :parameter: input_std_pattern_crc_list list
                crcRecord array
    """
    adding_stds = read_input_file(input_std_pattern_crc_list)

    for row in adding_stds:
        data_rate, resolution, colour_mapping, gamut = row
        new_std = (float(data_rate), resolution, colour_mapping, gamut)

        dict_to_df = {}
        dict_to_df.update(Standard=f'{new_std}', Pattern='N/a', CrcValue='N/a', CrcCount=0)
        crcRecord.append(dict_to_df, ignore_index=True)
        write_dataframe(crcRecord)
        print(f'Added standard: {new_std}')


def check_crc(gen_qx, analyse_qx, check_pattern_crc_list):
    """
    Checks (gets and prints) the CRCs of patterns for standards given in a list.

    :parameter: gen_qx object
                analyse_qx object
                check_pattern_crc_list list
    """
    crc_index_list = []
    crc_list = []
    check_std_crcs = []
    crc_count = 0
    no_crc = 0
    qx_settled = False
    version = gen_qx.about['Software_version']
    crcRecord = unpickle_crcRecord(version)

    check_std_crcs = read_input_file(check_pattern_crc_list)

    for row in check_std_crcs:
        data_rate, resolution, mapping, gamut, check_pattern, check_crc = row
        std = (float(data_rate), resolution, mapping, gamut)
        pattern_list = get_patterns(gen_qx, std)
        if check_pattern not in pattern_list:
            print(f'This standard does not support the test pattern: {row[4]}')
        else:
            gen_qx.generator.set_generator(resolution, mapping, gamut, check_pattern)
            qx_settled = gen_qx.generator.is_generating_standard(resolution, mapping, gamut, check_pattern)
            while not qx_settled:
                time.sleep(2)
                qx_settled = gen_qx.generator.is_generating_standard(resolution, mapping, gamut, check_pattern)
            print(f'generator set: {std} {check_pattern}')
            time.sleep(2)

            while no_crc == 0:
                no_crc = analyse_qx.analyser.get_crc_analyser()[0]['activePictureCrc']
            crc_count = set_crc_count(gen_qx)

            for index in range(crc_count):
                if crc_count > 1:
                    click.echo(f'This standard and pattern has {crc_count} CRC values.')
                    crc_index_list.append(crcRecord[(crcRecord['Standard'] == std) &
                                                    (crcRecord['Pattern'] == check_pattern)]['CrcValue'].index[index])
                    crc_list.append(crcRecord[(crcRecord['Standard'] == std) &
                                              (crcRecord['Pattern'] == check_pattern)]['CrcValue'][crc_index_list[index]])
                    print(f'The CRCs we have on record for {std} using {check_pattern} are {crc_list[crc_index_list[index]]}')
                    print(f"The CRCs the Qx/QxL is reading are {analyse_qx.analyser.get_crc_analyser()[index]['activePictureCrc']}")
                else:
                        crc_index = crcRecord[(crcRecord['Standard'] == std) &
                                              (crcRecord['Pattern'] == check_pattern)]['CrcValue'].index[0]
                        std_crc = crcRecord[(crcRecord['Standard'] == std) &
                                            (crcRecord['Pattern'] == check_pattern)]['CrcValue'][crc_index]
                        print(f'The CRC we have on record for {std} using {check_pattern} is {std_crc}')
                        print(f"The CRC the Qx/QxL is reading is {analyse_qx.analyser.get_crc_analyser()[index]['activePictureCrc']}")


def update_crc(gen_qx, update_crc_list):
    """
    Updates the golden master with the values provided in the input file.

    Pattern and CRC will have the same index so can use same variable for index.

    :parameter: gen_qx object
                update_crc_list list
    """
    crc_index_list = []
    crc_list = []
    crc_count = 0
    update_list = []
    version = gen_qx.about['Software_version']
    crcRecord = unpickle_crcRecord(version)

    update_list = read_input_file(update_crc_list)

    for row in update_list:
        data_rate, resolution, mapping, gamut, update_pattern, new_crc = row
        std = (float(data_rate), resolution, mapping, gamut)
        crc_count = set_crc_count(gen_qx)

        if crc_count > 1:
            click.echo(f'This standard has {crc_count} CRC values.')
            new_crc_index = click.prompt('Please choose which CRC you would like to edit: ', type=click.INT)
            for index in range(crc_count):
                crc_index_list.append(crcRecord[(crcRecord['Standard'] == std) &
                                                (crcRecord['Pattern'] == update_pattern)]['CrcValue'].index[index])
                crc_list.append(crcRecord[(crcRecord['Standard'] == std) &
                                          (crcRecord['Pattern'] == update_pattern)]['CrcValue'][crc_index_list[index]])
                std_ptn_index = crc_index_list[new_crc_index]
                click.echo(f'{index}: {crc_list[index]}')
        else:
            crc_index = crcRecord[(crcRecord['Standard'] == std) &
                                  (crcRecord['Pattern'] == update_pattern)]['CrcValue'].index[0]
            std_crc = crcRecord[(crcRecord['Standard'] == std) &
                                (crcRecord['Pattern'] == update_pattern)]['CrcValue'][crc_index]
            std_ptn_index = crcRecord[(crcRecord['Standard'] == std) &
                                      (crcRecord['Pattern'] == update_pattern)]['Pattern'].index[0]

        tmp_df = pd.DataFrame({'CrcValue': new_crc}, index=[std_ptn_index])
        crcRecord.update(tmp_df)
        print(f'CRC before update: {std_crc}')
        write_dataframe(crcRecord)
        updated_crc = crcRecord[(crcRecord['Standard'] == std) &
                                (crcRecord['Pattern'] == update_pattern)]
        print(f'Updated CRC: {updated_crc}.')


def main():
    """
    Entry point for the program.
    """
    gen_qx = generator_qx(GENERATOR)
    analyse_qx = analyser_qx(ANALYSER)
    welcome()
    user_action = menu()
    version = gen_qx.about['Software_version']
    if user_action == 1:
        update_crc_list = user_input(user_action)
        update_crc(gen_qx, update_crc_list)
    elif user_action == 2:
        add_std_list_file = user_input(user_action)
        crcRecord = unpickle_crcRecord(version)
        add_standard(add_std_list_file, crcRecord)
    elif user_action == 3:
        check_crc_list_file = user_input(user_action)
        crcRecord = unpickle_crcRecord(version)
        check_crc(gen_qx, analyse_qx, check_crc_list_file)
    elif user_action == 4:
        print('Generating CRC Records...')
        print('This may take some time.\n')
        standards_list, std_filter = gen_std_list(gen_qx, stds='nightly')
        generate_crcRecord(gen_qx, analyse_qx, standards_list, std_filter)


if __name__ == "__main__":
    main()
