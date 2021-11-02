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


# Set up logging
log = logging.getLogger(test_system_log)


# Get Env Variables
generator = os.getenv("GENERATOR_QX")
analyser = os.getenv("ANALYSER_QX")
test = os.getenv("TEST_QX")


def generator_qx(generator):
    """
    Basic generator_qx setup.

    * Bouncing Box set to False
    * Output copy set to False
    * Output source set to BNC
    * SDI Outputs set to generator
    """
    gen_qx = make_qx(hostname=generator)
    gen_qx.generator.bouncing_box = False
    gen_qx.generator.output_copy = False
    gen_qx.io.sdi_output_source = SDIIOType.BNC
    gen_qx.io.set_sdi_outputs(("generator", "generator", "generator", "generator"))
    log.info(f"Standard Verification Generator {gen_qx.hostname} setup complete.")
    return gen_qx


def analyser_qx(analyser):
    """
    Basic analyser_qx setup

    * Output/input(?) source set to BNC
    """
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
    # Using click.prompt checks for values outside the given range and
    # asks the user to re-enter a valid input if invalid input is given.
    user_choice_num = click.prompt('Please select your choice using the numbers: ', type=click.IntRange(1, len(actions)))
    print()
    if user_choice_num == 5:
        print('Bye!')
        exit()
    print(f'You chose: {user_choice_num}: {actions[user_choice_num-1]}.')
    return user_choice_num


def user_input(user_choice_num):
    """
    Takes the input from the user and returns a list.
    """
    input_std_list_file = click.prompt('Please enter the name of the input file containing the standards, patterns and CRC values.', type=click.STRING)
    return input_std_list_file


# Setting up filters to select standards.
def gen_std_list(gen_qx, stds="confidence_test_standards"):
    """
    This is to give the companion the same filters that are used as global fixtures
    in our pytest setup, as well as the decided nightly subset.
    """
    if not gen_qx.query_capability(OperationMode.IP_2110):
        if stds == "nightly": # Nightly filter, requirements agreed upon in meeting.
            standards_list = gen_qx.generator.get_matching_standards(
                [1.5],
                r"720.*|1920.*|2048.*|3840.*|4096.*",
                r"RGB.*|YCbCr:422:10|YCbCr:422:12|YCbCr:444:.*",
                r".*709|.*2020|HLG.*|PQ.*|S-Log3.*",
            )
        elif stds == "test": # Returns smaller subset than 'fast', quicker testing.
            standards_list = gen_qx.generator.get_matching_standards(
                [1.5], r"1920.*", r"YCbCr:422:10", r".*709"
            )
        elif stds == "fast": # This filter was added to speed up testing and dev. It returns 10 stds.
            standards_list = gen_qx.generator.get_matching_standards(
                [1.5, 3.0], r"(1920x1080|1280x720)[i|p]50", "YCbCr:422:10", ".Rec.709"
            )
        elif stds == "confidence_test_standards":
            standards_list = gen_qx.generator.get_matching_standards(
                [1.5, 3.0, 6.0, 12.0],
                r'\d+x\d+p\d+',
                r'YCbCr:422:10',
                r'.*709'
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


def check_standards(gen_qx, standards_list):
    """
    Debugging method. Purely used to check the standards list.
    """
    for std in standards_list:
        print(type(std))


def check_patterns(gen_qx, standards_list):
    """
    Debugging method. Purely used to check the pattern list.

    std[1] = resolution
    std[2] = colour mapping
    std[3] = gamut
    """
    for std in standards_list:
        test_patterns = gen_qx.generator.get_test_patterns(std[1], std[2], std[3])
    print(test_patterns)


def get_patterns(gen_qx, std):
    """
    Retrieves all supported patterns for a given standard.

    std[1] = resolution
    std[2] = colour mapping
    std[3] = gamut
    """
    try:
        test_patterns = gen_qx.generator.get_test_patterns(std[1], std[2], std[3])
        return test_patterns
    except GeneratorException as pattErr:
        log.error(f"An error occurred while getting test_patterns: {pattErr}")


# Possibly able to remove this?
def get_subimages(gen_qx):
    """
    Gets the subimages for a standard, based on it's level, data_rate and links.
    """
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
    """
    Gets the number of crcs for the standard and pattern that is currently being generated.
    """
    crc_count = len(gen_qx.analyser.get_crc_analyser())
    return crc_count


# Method to work out total number of records that will end up in the dataframe
# to pass to bar() for the loading bar. W.i.P
def total_iterations(gen_qx, standards_list):
    """
    Loading bar that proved quite useful, mainly by providing an eta of completion.
    """
    total = 0
    crc_count = 0
    for std in standards_list:
        test_patterns = get_patterns(gen_qx, std)
        crc_count = set_crc_count(gen_qx)
        total += len(test_patterns) * crc_count
    return total


def generate_golden_master(gen_qx, anlyser_qx, standards_list):
    """
    Main method that generates and writes the golden_master.
    """
    qx_crcs = []
    qx_settled = False
    crc_count = 0
    try:  # 9329 original number
        #with alive_bar(total_iterations(gen_qx, standards_list)) as bar:
        for std in standards_list:
            data_rate, resolution, mapping, gamut = std
            try:
                test_patterns = get_patterns(gen_qx, std)
                for pattern in test_patterns:
                    try:
                        gen_qx.generator.set_generator(resolution, mapping, gamut, pattern)
                        time.sleep(3)
                        crc_count = set_crc_count(gen_qx)
                        qx_settled = anlyser_qx.generator.is_generating_standard(resolution, mapping, gamut, pattern)
                        while qx_settled is False:
                            qx_settled = anlyser_qx.generator.is_generating_standard(resolution, mapping, gamut, pattern)
                        try:
                            for crc_value in anlyser_qx.analyser.get_crc_analyser():
                                try:
                                    print(f'retrieved using qx: {std}, {pattern}, {crc_value["activePictureCrc"].upper()}')
                                    dict_to_df = {}
                                    dict_to_df.update(Standard=eval(f'{std}'), Pattern=eval(f'str("{pattern}")'), CrcValue=eval(f'str("{crc_value["activePictureCrc"]}")'), CrcCount=eval(f'{crc_count}'))
                                    qx_crcs.append(dict_to_df)
                                    # bar()
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
        write_dataframe(qx_dataframe)
    except KeyError as pickleErr:
        log.error(f"An error occurred while pickling: {pickleErr}")


def unpickle_golden_master():
    """
    Unpickles the pkl file and returns a pandas dataframe.

    This is to keep the code as DRY as possible.
    """
    unpickled_crcs = pd.read_pickle('./golden_master-confidence.pkl')
    return unpickled_crcs


def write_dataframe(dataframe):
    """
    Writes the given dataframe to disc.

    This is to keep the code as DRY as possible.
    """
    records = open("golden_master-confidence.pkl", "wb")
    pickler = pickle.Pickler(records)
    pickler.dump(dataframe)
    records.close()


def read_input_file(input_std_pattern_crc_list):
    """
    Reads the given file for input for use in 3 methods:
        * add_standard()
        * check_crc()
        * update_crc()

    This is to keep the code as DRY as possible.
    """
    with open(input_std_pattern_crc_list) as reader:
        contents = reader.read().split('\n')

    input_stds = []
    for line in contents:
        if line == '':
            continue
        input_stds.append(line.split(','))

    return input_stds


def add_standard(input_std_pattern_crc_list, golden_master):
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
    entire golden_master.
    """
    adding_stds = read_input_file(input_std_pattern_crc_list)

    for row in adding_stds:
        data_rate, resolution, colour_mapping, gamut = row
        new_std = (float(data_rate), resolution, colour_mapping, gamut)

        dict_to_df = {}
        # Only updating the golden master with a standard field, as the test_patterns that are relevant for that standard will
        # be generated on the qx, as will the CRC values for the test patterns.
        dict_to_df.update(Standard=f'{new_std}', Pattern='N/a', CrcValue='N/a', CrcCount=0)
        golden_master.append(dict_to_df, ignore_index=True)
        write_dataframe(golden_master)
        print(f'Added standard: {new_std}')


def check_crc(gen_qx, anlyser_qx, check_pattern_crc_list):
    """
    Checks (gets and prints) the CRCs of patterns for standards given in a list.
    """
    crc_index_list = []
    crc_list = []
    check_std_crcs = []
    crc_count = 0
    no_crc = 0
    qx_settled = False
    golden_master = unpickle_golden_master()

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
                no_crc = anlyser_qx.analyser.get_crc_analyser()[0]['activePictureCrc']
            crc_count = set_crc_count(gen_qx)

            for index in range(crc_count):
                if crc_count > 1:
                    click.echo(f'This standard and pattern has {crc_count} CRC values.')
                    crc_index_list.append(golden_master[(golden_master['Standard'] == std) &
                                                        (golden_master['Pattern'] == check_pattern)]['CrcValue'].index[index])
                    crc_list.append(golden_master[(golden_master['Standard'] == std) &
                                                  (golden_master['Pattern'] == check_pattern)]['CrcValue'][crc_index_list[index]])
                    print(f'The CRCs we have on record for {std} using {check_pattern} are {crc_list[crc_index_list[index]]}')
                    print(f"The CRCs the Qx/QxL is reading are {anlyser_qx.analyser.get_crc_analyser()[index]['activePictureCrc']}")
                else:
                        crc_index = golden_master[(golden_master['Standard'] == std) &
                                                  (golden_master['Pattern'] == check_pattern)]['CrcValue'].index[0]
                        std_crc = golden_master[(golden_master['Standard'] == std) &
                                                (golden_master['Pattern'] == check_pattern)]['CrcValue'][crc_index]
                        print(f'The CRC we have on record for {std} using {check_pattern} is {std_crc}')
                        print(f"The CRC the Qx/QxL is reading is {anlyser_qx.analyser.get_crc_analyser()[index]['activePictureCrc']}")


def update_crc(gen_qx, update_crc_list):
    """
    Updates the golden master with the values provided in the input file.
    """
    crc_index_list = []
    crc_list = []
    crc_count = 0
    update_list = []
    golden_master = unpickle_golden_master()

    update_list = read_input_file(update_crc_list)

    for row in update_list:
        data_rate, resolution, mapping, gamut, update_pattern, new_crc = row
        std = (float(data_rate), resolution, mapping, gamut)
        crc_count = set_crc_count(gen_qx)

        if crc_count > 1:
            click.echo(f'This standard has {crc_count} CRC values.')
            new_crc_index = click.prompt('Please choose which CRC you would like to edit: ', type=click.INT)
            for index in range(crc_count):
                crc_index_list.append(golden_master[(golden_master['Standard'] == std) &
                                                    (golden_master['Pattern'] == update_pattern)]['CrcValue'].index[index])
                crc_list.append(golden_master[(golden_master['Standard'] == std) &
                                              (golden_master['Pattern'] == update_pattern)]['CrcValue'][crc_index_list[index]])
                std_ptn_index = crc_index_list[new_crc_index] # Pattern and CRC will have the same index
                click.echo(f'{index}: {crc_list[index]}')
        else:
            crc_index = golden_master[(golden_master['Standard'] == std) &
                                      (golden_master['Pattern'] == update_pattern)]['CrcValue'].index[0]
            std_crc = golden_master[(golden_master['Standard'] == std) &
                                    (golden_master['Pattern'] == update_pattern)]['CrcValue'][crc_index]
            std_ptn_index = golden_master[(golden_master['Standard'] == std) &
                                          (golden_master['Pattern'] == update_pattern)]['Pattern'].index[0]

        tmp_df = pd.DataFrame({'CrcValue': new_crc}, index=[std_ptn_index])
        golden_master.update(tmp_df)
        print(f'CRC before update: {std_crc}')
        write_dataframe(golden_master)
        updated_crc = golden_master[(golden_master['Standard'] == std) &
                                    (golden_master['Pattern'] == update_pattern)]
        print(f'Updated CRC: {updated_crc}.')


def main():
    """
    Entry point for the program.
    """
    gen_qx = generator_qx(generator)
    anlyser_qx = analyser_qx(analyser)
    welcome()
    user_action = menu()
    if user_action == 1:
        update_crc_list = user_input(user_action)
        update_crc(gen_qx, update_crc_list)
    elif user_action == 2:
        add_std_list_file = user_input(user_action)
        golden_master = unpickle_golden_master()
        add_standard(add_std_list_file, golden_master)
    elif user_action == 3:
        check_crc_list_file = user_input(user_action)
        golden_master = unpickle_golden_master()
        check_crc(gen_qx, anlyser_qx, check_crc_list_file)
    elif user_action == 4:
        print('Generating Golden Master...')
        print('This may take some time.\n')
        standards_list = gen_std_list(gen_qx, stds='confidence_test_standards')
        generate_golden_master(gen_qx, anlyser_qx, standards_list)


if __name__ == "__main__":
    main()
