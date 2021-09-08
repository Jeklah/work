"""
A verification tool to check that the standards that are being generated are the correct standards.
This will be done by storing the APCRC of a generated standard, upon first run of this script.
When this script is run after the first run, it will check the APCRC of the generated standard
against the stored APCRC for that standard. If the standard isn't recognised, it will store the APCRC
for future use, or inform the user that it is an invalid standard.
"""
import pdb
import os
import sys
import time

# import click
import ctypes as ct

# import pandas as pd
# import numpy as np
import logging

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("ignore")
from test_system.factory import make_qx
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.io import SDIIOType
from test_system.logconfig import test_system_log
# from test_system.models.qxseries.qxexception import QxException
from test_system.models.qxseries.analyser import AnalyserException
from test_system.models.qxseries.generator import GeneratorException
from test_system.models.qxseries.qxexception import QxException

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

# Get environment constants
generator = os.getenv("GENERATOR_QX")
analyser = os.getenv("ANALYSER_QX")
test = os.getenv("TEST_QX")


def generator_qx(generator):
    gen_qx = make_qx(hostname=generator)
    gen_qx.generator.bouncing_box = False
    gen_qx.generator.output_copy = True
    gen_qx.io.sdi_output_source = SDIIOType.BNC
    gen_qx.io.set_sdi_outputs(("generator", "generator", "generator", "generator"))
    log.info(f"Standard Verification Generator {gen_qx.hostname} setup complete.")
    return gen_qx


def analyser_qx(analyser):
    anlyser_qx = make_qx(hostname=analyser)
    anlyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f"Standard Verification Analyser {anlyser_qx.hostname} setup complete.")
    return anlyser_qx


# Methods for controlling the Sx
def loadPhabLib():
    phablib = ct.cdll.LoadLibrary("./PhabrixRemoteSo.so")
    return phablib


def sx_openConnection(phabLib):
    connection = phabLib.OpenConnection(ct.c_char_p(SX_IP), ct.c_uint(PORT))
    return connection


def sx_getCrcFromGen(phabLib, connection, standards_list):
    sx_count = 0
    sx_crc = []
    try:
        stringBuffer = ct.create_string_buffer(10)
        time.sleep(2)
        phabLib.PhSendMsg(
            ct.c_char_p(SX_IP),
            ct.c_uint(PORT),
            ct.c_uint(MSG_GET_TEXT),
            ct.c_uint(COM_STATUS_LINK_1_ACTIVE_PICTURE_CHECKSUM),
            ct.c_int(0),
            ct.c_int(0),
            ct.c_char_p(b""),
            stringBuffer,
            ct.pointer(ct.c_uint()),
            10,
        )
        for crc in str(stringBuffer.value.decode("utf-8")):
            print(f'{sx_count}: CRC Value is: {str(stringBuffer.value.decode("utf-8"))}')
        sx_count += 1
    except GeneratorException as err:
        log.error(f"{err} has occurred")


def getCrc(gen_qx, anlyser_qx, standards_list):
    count = 0
    crcs = []
    settled = False
    phabLib = loadPhabLib()
    #breakpoint()
    connection = sx_openConnection(phabLib)
    for std in standards_list:
        test_patterns = get_patterns(gen_qx, standards_list)
        for pattern in test_patterns:
            count += 1
            try:
                gen_qx.generator.set_generator(std[1], std[2], std[3], pattern)
                std_params = list(std)
                settled = anlyser_qx.generator.is_generating_standard(std[1], std[2], std[3], pattern)
                while settled == False:
                    settled = anlyser_qx.generator.is_generating_standard(std[1], std[2], std[3], pattern)
                try:
                    time.sleep(3)
                    (std_params[1], std_params[2], std_params[3]) = anlyser_qx.analyser.get_analyser_status()
                    #sx_getCrcFromGen(phabLib, connection, standards_list)
                    for crc_values in anlyser_qx.analyser.get_crc_analyser():
                        crcs.append(std_params + list(crc_values["activePictureCrc"]))
                        #with open('crc_golden_master.txt', 'a') as writer:
                        #    writer.write(std_params,  str(list(crc_values["activePictureCrc"])))
                        print(f'{count}: retrieved from qx {std}, {pattern}, {crc_values["activePictureCrc"]}')
                except AnalyserException as analyserErr:
                    log.error(f"analyser error: {analyserErr}")
            except GeneratorException as genErr:
                log.error(f"a generator error has occured: {genErr}")


def get_patterns(gen_qx, standards_list):
    try:
        for std in standards_list:
            print(type(std))
            test_patterns = gen_qx.generator.get_test_patterns(std[1], std[2], std[3])
        return test_patterns
    except GeneratorException as patternErr:
        log.error(f"an error occured while getting test_patterns: {patternErr}")


def get_stds(gen_qx, stds="quick"):
    if not gen_qx.query_capability(OperationMode.IP_2110):
        if stds == "confidence":
            standards = gen_qx.generator.get_matching_standards(
                [1.5, 3.0, 6.0, 12.0], r"\d+x\d+p\d+", r"YCbCr:422:10", r".*709"
            )
        elif stds == "smoke":
            standards = gen_qx.generator.get_matching_standards(
                [3.0, 12.0], r"1920.*|3840.*", r"Y.*", r".*709"
            )
        elif stds == "quick":
            standards = gen_qx.generator.get_matching_standards(
                [12.0], r"1920.*|3840.*", r"YCbCr:422:10", r".*709"
            )
        elif stds == "all":
            all_standards = gen_qx.generator.get_standards()
            standards = [[data_rate, resolution, colour_map, gamut]
                    for data_rate in all_standards
                    for resolution in all_standards[data_rate]
                    for colour_map in all_standards[data_rate][resolution]
                    for gamut in all_standards[data_rate][resolution][colour_map]]
        else:
            print(f"{gen_qx.hostname} is currently in IP 2110 mode. Please switch to SDI mode.")
        return standards

def check_patterns(gen_qx, standards_list):
    try:
        for std in standards_list:
            test_patterns = gen_qx.generator.get_test_patterns(std[1], std[2], std[3])
            for ptn in test_patterns:
                print(f'{ptn}')
        return test_patterns
    except QxException:
        log.error('An error occurred while checking patterns.')


def qx_getCrcFromGen(gen_qx, anlyser_qx, standards_list):
    qx_crcs = []
    settled = False
    qx_count = 0
    try:
        for std in standards_list:
            # print(f'generating {std} now...')
            try:
                test_patterns = get_patterns(gen_qx, std)
                for pattern in test_patterns:
                    qx_count += 1
                    gen_qx.generator.set_generator(std[1], std[2], std[3], pattern)
            except GeneratorException as genErr:
                log.error(f"generator error: {genErr}")
    except GeneratorException as stdErr:
        log.error(f"standard list error: {stdErr}")


def populate_golden_master(gen_qx, anlyser_qx):
    valid_standards = gen_qx.generator.get_standards()
    colour = list(gen_qx.generator.get_standards(standard_params=True)["colour_spaces"])


def check_golden_master_exists():
    csvFile_name = "APCRC.csv"
    if not os.path.isfile(csvFile_name):
        open(csvFile_name, "x")
    else:
        pass


def check_stds(standards, gen_qx, anlyser_qx):
    for std in standards:
        print(type(std))

def main():
    # Initialisation
    gen_qx = generator_qx(generator)
    anlyser_qx = analyser_qx(analyser)
    standards_list = get_stds(gen_qx)
    #check_patterns(gen_qx, standards_list)
    #check_stds(standards_list, gen_qx, anlyser_qx)
    #qx_getCrcFromGen(gen_qx, anlyser_qx, standards_list)
    getCrc(gen_qx, anlyser_qx, standards_list)
    # loadedLib = loadPhabLib()
    # conn = sx_openConnection(loadedLib)
    # sx_getCrcFromGen(gen_qx, loadedLib, conn, standards_list)


if __name__ == "__main__":
    main()
