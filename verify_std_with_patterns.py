"""
A verification tool to check that the standards that are being generated are
the correct standards. This will be done by storing the APCRC of a generated
standard on first run of this tool.
When this tool is run after the golden master has been generated, it will
check the APCRC of the generated standard with the stored APCRC for that
standard in the golden master to make sure they are the same. If it is not
already stored, it will store it (adding new standard) and if it is wrong/
invalid then it will inform the user.
"""
import os
import sys
import time
import click
import pickle
import logging
import ctypes as ct
import pandas as pd
if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")
from alive_progress import alive_bar # Loading bar library written in pure Python.
from test_system.factory import make_qx
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.io import SDIIOType
from test_system.logconfig import test_system_log
from test_system.models.qxseries.analyser import AnalyserException
from test_system.models.qxseries.generator import GeneratorException
from test_system.testexception import TestException


# Constants for control of the Sx
SX_IP = b"192.168.0.161"
PORT = 2100
MSG_GET_TEXT = 20
COM_MAIN_TAB_SELECT = 2
COM_STATUS_LINK_1_ERROR_TITLE = 438
COM_STATUS_LINK_1_ACTIVE_PICTURE_CHECKSUM = 675
COM_ANLYS_INP_SEL = 573


# Set up logging
log = logging.getLogger(test_system_log)


# Get Env Variables
generator = os.getenv("GENERATOR_QX")
analyser = os.getenv("ANALYSER_QX")
test = os.getenv("TEST_QX")


def generator_qx(generator):
    gen_qx = make_qx(hostname=generator)
    gen_qx.generator.bouncing_box = False
    gen_qx.generator.output_copy = False
    gen_qx.io.sdi_output_source = SDIIOType.BNC
    gen_qx.io.set_sdi_outputs(("generator", "generator", "generator", "generator"))
    log.info(f"Standard Verification Generator {gen_qx.hostname} setup complete.")
    return gen_qx


def analyser_qx(analyser):
    anlyser_qx = make_qx(hostname=analyser)
    anlyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f"Standard Verification Analyser {anlyser_qx.hostname} setup complete.")
    return anlyser_qx


def welcome():
    """
    Welcome message for the user.
    """
    click.secho('Welcome to the CRC Standard Checker tool.', bg='green', fg='black', bold=True)


def menu():
    """
    Presents the user with a menu, listing the choice of actions the user would like
    to take.
    """
    actions = [
                'Update Standard',
                'Add Standard',
                'Check Standard CRC',
                'Generate Golden Master',
                'Exit'
               ]
    print('Please choose what you would like to do from the list below.')
    for choice in actions:
        print(f'{actions.index(choice)+1}: {choice}')

    user_choice_num = click.prompt('Please select your choice using the numbers: ', type=click.IntRange(1, len(actions)))
    print()
    if user_choice_num == 5:
        print('Bye!')
        exit()
    print(f'You chose: {user_choice_num}: {actions[user_choice_num-1]}.')
    return user_choice_num


def user_input(user_choice_num):
    data_rate = click.prompt('Please enter your desired data rate: ', type=click.FLOAT)
    resolution = click.prompt('Please enter your desired resolution: ', type=click.STRING)
    mapping = click.prompt('Please enter your desired mapping: ', type=click.STRING)
    gamut = click.prompt('Please enter your desired gamut (including data rate): ', type=click.STRING)

    if user_choice_num == 1:
        pattern = click.prompt('Please enter the name of the test pattern you would like to update: ', type=click.STRING)
        new_crc = click.prompt('Please enter the new CRC value: ', type=click.STRING)
        return data_rate, resolution, mapping, gamut, pattern, new_crc
    elif user_choice_num == 2:
        return data_rate, resolution, mapping, gamut
    elif user_choice_num == 3:
        pattern = click.prompt('Please enter the name of the test pattern you would like to check the CRC for: ', type=click.STRING)
        return data_rate, resolution, mapping, gamut, pattern



# Setting up filters to select standards.
def get_stds(gen_qx, stds="test"):
    if not gen_qx.query_capability(OperationMode.IP_2110):
        if stds == "nightly": # Nightly filter, requirements agreed upon in meeting.
            standards_list = gen_qx.generator.get_matching_standards(
                [1.5],
                r"720.*|1920.*|2048.*|3840.*|4096.*",
                r"RGB.*|YCbCr:422:10|YCbCr:422:12|YCbCr:444:.*",
                r".*709|.*2020|HLG.*|PQ.*|S-Log3.*",
            )
        elif stds == "test":
            standards_list = gen_qx.generator.get_matching_standards(
                [1.5], r"1920.*", r"YCbCr:422:10", r".*709"
            )
        elif stds == "fast": # This filter was added to speed up testing and dev. It returns 10 stds.
            standards_list = gen_qx.generator.get_matching_standards(
                [1.5, 3.0], r"(1920x1080|1280x720)[i|p]50", "YCbCr:422:10", ".Rec.709"
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
    return standards_list


# Method to check standards_list mainly used while developing.
def check_standards(gen_qx, standards_list):
    iterator = iter(standards_list)
    sentinel = object()
    while True:
        std = next(iterator, sentinel)
        if std is sentinel:
            break
        print(type(std))


# Similar to above, method to check the patterns for the standards in standards_list.
# Used for development.
def check_patterns(gen_qx, standards_list):
    iterator = iter(standards_list)
    sentinel = object()
    while True:
        std = next(iterator, sentinel)
        if std is sentinel:
            break
        test_patterns = gen_qx.generator.get_test_patterns(std[1], std[2], std[3])
    print(test_patterns)


# Get all the patterns for a given standard.
def get_patterns(gen_qx, std):
    try:
        test_patterns = gen_qx.generator.get_test_patterns(std[1], std[2], std[3])
        return test_patterns
    except GeneratorException as pattErr:
        log.error(f"An error occurred while getting test_patterns: {pattErr}")


# Get the sub-images for a given standard, depending on it's level, data_rate and links.
def get_subimages(gen_qx, std):
    std_lvl, data_rate, links = (
        gen_qx.analyser.parse_analyser_status(gen_qx.analyser.get_analyser_status())[
            "type"
        ]["level"],
        gen_qx.analyser.parse_analyser_status(gen_qx.analyser.get_analyser_status())[
            "type"
        ]["data_rate_Gb"],
        gen_qx.analyser.parse_analyser_status(gen_qx.analyser.get_analyser_status())[
            "type"
        ]["link_number"],
    )
    if std_lvl == 'A':
        if data_rate <= 3.0 and links == 1:
            sub_images = ["subImage1"]
        elif data_rate <= 3.0 and links > 3:
            sub_images = ["subImage1", "subImage2", "subImage3", "subImage4"]
        elif links == 2:
            sub_images = ["subImage1"]
        else:
            sub_images = ["subImage1", "subImage2", "subImage3", "subImage4"]
            log.error(f"{gen_qx.hostname} - Assuming QL 3GA: {data_rate}")
    elif std_lvl == 'B':
        if data_rate >= 3.0 and links == 1:
            sub_images = ["subImage1", "linkBSubImage1"]
        elif data_rate >= 3.0 and links == 4:
            sub_images = ["subImage1", "subImage2", "subImage3", "subImage4",
                          "linkBSubImage1", "linkBSubImage2", "linkBSubImage3", "linkBSubImage4"]
        else:
            raise TestException(f"{gen_qx.hostname} - Failed to determine sub images [LVL B]: {data_rate}")
    else:
        raise TestException(f"{gen_qx.hostname} - Unrecognised standard level: {std_lvl}")
    return sub_images


def set_crc_count(gen_qx):
    crc_count = len(gen_qx.analyser.get_crc_analyser())
    return crc_count


# Method to work out total number of records that will end up in the dataframe
# to pass to bar() for the loading bar. W.i.P
def total_iterations(gen_qx, standards_list):
    total = 0
    crc_count = 0
    for std in standards_list:
        test_patterns = get_patterns(gen_qx, std)
        crc_count = set_crc_count(gen_qx)
        total += len(test_patterns) * crc_count
    return total


def qx_getCrc(gen_qx, anlyser_qx, standards_list):
    qx_crcs = []
    qx_settled = False
    crc_count = 0
    try:  # 9329 original number
        with alive_bar(total_iterations(gen_qx, standards_list)) as bar:
            # for std in standards_list:
            std_iterator = iter(standards_list)
            std_sentinel = object()
            try:
                while True:
                    std = next(std_iterator, std_sentinel)
                    if std is std_sentinel:
                        break
                    test_patterns = get_patterns(gen_qx, std)
                    # for pattern in test_patterns:
                    ptn_iterator = iter(test_patterns)
                    ptn_sentinel = object()
                    try:
                        while True:
                            pattern = next(ptn_iterator, ptn_sentinel)
                            if pattern is ptn_sentinel:
                                break
                            gen_qx.generator.set_generator(std[1], std[2], std[3], pattern)
                            crc_count = set_crc_count(gen_qx)
                            std_params = list(std)
                            qx_settled = anlyser_qx.generator.is_generating_standard(std[1], std[2], std[3], pattern)
                            while qx_settled is False:
                                qx_settled = (anlyser_qx.generator.is_generating_standard(std[1], std[2], std[3], pattern))
                            try:
                                time.sleep(3)
                                (
                                    std_params[1],
                                    std_params[2],
                                    std_params[3],
                                ) = anlyser_qx.analyser.get_analyser_status()
                                # for crc_value in anlyser_qx.analyser.get_crc_analyser():
                                crc_iterator = iter(anlyser_qx.analyser.get_crc_analyser())
                                crc_sentinel = object()
                                try:
                                    while True:
                                        crc_value = next(crc_iterator, crc_sentinel)
                                        if crc_value is crc_sentinel:
                                            break
                                        print(f'retrieved using qx: {std}, {pattern}, {crc_value["activePictureCrc"].upper()}')
                                        dict_to_df = {}
                                        dict_to_df.update(Standard=[eval(f'{std}')], Pattern=[eval(f'str("{pattern}")')], CrcValue=[eval(f'str("{crc_value["activePictureCrc"]}")')], CrcCount=[eval(f'{crc_count}')])
                                        qx_crcs.append(dict_to_df)
                                        bar()
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
        results = open("crc_dataframe.pkl", "wb")
        pickler = pickle.Pickler(results)
        pickler.dump(qx_dataframe)
        results.close()
    except KeyError as pickleErr:
        log.error(f"An error occurred while pickling: {pickleErr}")


def unpickle_golden_master():
    unpickled_crcs = pd.read_pickle('./crc_dataframe.pkl')
    return unpickled_crcs


def write_dataframe(dataframe):
    records = open("crc_dataframe.pkl", "wb")
    pickler = pickle.Pickler(records)
    pickler.dump(dataframe)
    records.close()


def add_standard(data_rate, resolution, mapping, gamut, dataframe):
    new_std = (data_rate, resolution, mapping, gamut)
    dict_to_df = {}
    dict_to_df.update(Standard=[eval(f"{new_std}")])
    dataframe.append(dict_to_df, ignore_index=True)
    write_dataframe(dataframe)


def check_crc(gen_qx, data_rate, resolution, mapping, gamut, pattern):
    crc_index_list = []
    crc_list = []
    crc_count = 0
    golden_master = unpickle_golden_master()
    std = (data_rate, resolution, mapping, gamut)
    crc_count = set_crc_count(gen_qx)

    if crc_count > 1:
        click.echo(f'This standard has {crc_count} CRC values.')
        for index in range(crc_count):
            crc_index_list.append(golden_master.loc[golden_master['Standard'].apply(lambda x: x == [std]) & \
                                                    golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'].index[index])
            crc_list.append(golden_master.loc[golden_master['Standard'].apply(lambda x: x == [std]) & \
                                              golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'][crc_index_list[index]])
            click.echo(f'{index}: CRC {index+1}: {crc_list[index]}.')
    else:
        crc_index = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [std]) & \
                                      golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'].index[0]
        std_crc = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [std]) & \
                                    golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'][crc_index]
        print(f'The CRC for Standard {std} using pattern {pattern} is {std_crc}')


def update_crc(gen_qx, data_rate, resolution, mapping, gamut, pattern, new_crc):
    crc_index_list = []
    crc_list = []
    crc_count = 0
    golden_master = unpickle_golden_master()
    std = (data_rate, resolution, mapping, gamut)
    crc_count = set_crc_count(gen_qx)
    new_crc = '[' + str(new_crc) + ']'

    if crc_count > 1:
        click.echo(f'This standard has {crc_count} CRC values.')
        for index in range(crc_count):
            crc_index_list.append(golden_master.loc[golden_master['Standard'].apply(lambda x: x == [std]) & \
                                                    golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'].index[index])
            crc_list.append(golden_master.loc[golden_master['Standard'].apply(lambda x: x == [std]) & \
                                              golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'][crc_index_list[index]])
            click.echo(f'{index}: {crc_list[index]}')
        new_crc_index = click.prompt('Please choose which CRC you would like to edit: ', type=click.INT)
        std_ptn_index = crc_index_list[new_crc_index]
    else:
        std_ptn_index = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [std]) & \
                                          golden_master['Pattern'].apply(lambda y: y == [pattern])]['Pattern'].index[0]
    tmp_df = pd.DataFrame({'CrcValue': [new_crc]}, index=[std_ptn_index])
    golden_master.update(tmp_df)
    write_dataframe(golden_master)
    updated_crc = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [std]) & \
                                    golden_master['Pattern'].apply(lambda y: y == [pattern])]
    print(f'Updated CRC: {updated_crc}.')


# Methods for controlling the Sx
def loadPhabLib():
    phabLib = ct.cdll.LoadLibrary("./PhabrixRemoteSo.so")
    return phabLib


def sx_openConnection(phabLib):
    connection = phabLib.OpenConnection(ct.c_char_p(SX_IP), ct.c_uint(PORT))
    return connection


def sx_getCrc(gen_qx, connection, standards_list):
    # sx_crcs = [] # Not used?
    sx_count = 0
    phablib = loadPhabLib()
    try:
        crcValue = ct.create_string_buffer(10)
        time.sleep(2)
        phablib.PhSendMsg(
            ct.c_char_p(SX_IP),
            ct.c_uint(PORT),
            ct.c_uint(MSG_GET_TEXT),
            ct.c_uint(COM_STATUS_LINK_1_ACTIVE_PICTURE_CHECKSUM),
            ct.c_int(0),
            ct.c_int(0),
            ct.c_char_p(b""),
            crcValue,
            ct.pointer(ct.c_uint()),
            10,
        )
        for crc in str(crcValue.value.decode("utf-8")):
            print(f'{sx_count}: CRC Value is : {str(crcValue.value.decode("utf-8"))}')
        sx_count += 1
    except GeneratorException as err:
        log.error(f'{err} has occurred')


def main():
    gen_qx = generator_qx(generator)
    anlyser_qx = analyser_qx(analyser)
    welcome()
    user_action = menu()
    # standards_list = read_test_standards()
    standards_list = get_stds(gen_qx, stds="fast")
    # check_standards(gen_qx, standards_list)
    # check_patterns(gen_qx, standards_list)
    if user_action == 1:
        data_rate, resolution, mapping, gamut, pattern, new_crc = user_input(user_action)
        update_crc(gen_qx, data_rate, resolution, mapping, gamut, pattern, new_crc)
    elif user_action == 2:
        data_rate, resolution, mapping, gamut = user_input(user_action)
        dataframe = unpickle_golden_master()
        add_standard(data_rate, resolution, mapping, gamut, dataframe)
    elif user_action == 3:
        data_rate, resolution, mapping, gamut, pattern = user_input(user_action)
        check_crc(gen_qx, data_rate, resolution, mapping, gamut, pattern)
    elif user_action == 4:
        print('Generating Golden Master...')
        print('This may take some time.\n')
        qx_getCrc(gen_qx, anlyser_qx, standards_list)


if __name__ == "__main__":
    main()
