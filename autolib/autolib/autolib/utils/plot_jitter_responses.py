#!/usr/bin/env python3
"""\
Usage: plot_jitter_frequency_responses.py GENERATOR_HOSTNAME ANALYSER_HOSTNAME [--plots=<NO_OF_PLOTS>] [--amplitude=<JITTER_AMP>] [--pathological] [--dumpcsv]

Plot jitter insertion frequency sweep vs jitter band reading for 1.5G / 3G / 6G and 12G standards onto graph

Arguments:
    GENERATOR_HOSTNAME                      Hostname of generator unit
    ANALYSER_HOSTNAME                       Hostname of analyser unit

Options:
    -p NO_OF_PLOTS --plots=NO_OF_PLOTS      The number of plots / data samples to display on resulting graph  [default: 100]
    -a JITTER_AMP --amplitude=JITTER_AMP    The base jitter insertion amplitude to use across the jitter frequency sweep  [default: 0.2]
    --pathological                          Boolean value which will set max pathological insertion if True
    --dumpcsv                               Dump CSV files containing the graph data
    -h, --help                              Display this help and exit

"""
import string
import datetime
from autolib.factory import make_qx
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.input_output import SDIIOType
from docopt import docopt
import matplotlib.pyplot as plt
import numpy as np
import time
import random


def _step_through_jitter_frequency(amp, steps):
    """Generate frequency values based on number of steps,
    Increase jitter frequency in logarithmic fashion to provide jitter UI values

    :arg amp:    Base amplitude for test (UI)
    :arg steps:  Number of frequency values to generate to provide log plot

    :return list of jitter frequency values used in test (raw x axis values)
    :return tuple of lists containing jitter UI readings for each frequency band (raw y axis values)
    """

    jitter_freq = []
    jitter_ui_10 = []
    jitter_ui_100 = []
    jitter_ui_1000 = []
    jitter_ui_10000 = []
    jitter_ui_100000 = []

    # Create plot values between 2 x numbers in log.
    # Numbers should be min frequency to max frequency of jitter insertion
    plt_nodes = np.logspace(1, 7, num=steps, endpoint=True)
    print("Node steps: \n%s" % plt_nodes)

    # Apply first time jitter insertion (avoid initial spike)
    generator_qx.generator.jitter_insertion("Sine", amp, plt_nodes[0])
    time.sleep(4)

    for node in plt_nodes:
        # Apply jitter insertion
        generator_qx.generator.jitter_insertion("Sine", amp, int(node))

        # Write current frequency of insertion to appropriate list
        jitter_freq.append(node)

        time.sleep(1)

        # Get a dict of all frequency band jitter UI values
        all_ui_values = analyser_qx.jitter.get_jitter_values()

        # Write current ui reading to arrays
        jitter_ui_10.append(all_ui_values["10_Hz"])
        jitter_ui_100.append(all_ui_values["100_Hz"])
        jitter_ui_1000.append(all_ui_values["1000_Hz"])
        jitter_ui_10000.append(all_ui_values["10000_Hz"])
        jitter_ui_100000.append(all_ui_values["100000_Hz"])

        print(analyser_qx.hostname + " - Frequency: %s\t Jitter UI: %s" % (node, all_ui_values))

    # Zero the unit
    generator_qx.generator.jitter_insertion("Disabled", 0.2, 10)

    return [jitter_freq, (jitter_ui_10, jitter_ui_100, jitter_ui_1000, jitter_ui_10000, jitter_ui_100000)]


def _plot_jitter_ui(plot, freq_data, raw_jitter_data, dumpcsv):
    """ Plot frequency vs jitter band reading onto graph

    :arg plot: pyplot figure object on which to plot data
    :arg freq_data: list of measured frequency data
    :arg raw_jitter_data: list of lists: Jitter value data (1 list per jitter frequency)
    """

    # Process the data into numpy arrays
    data_size = np.size(freq_data)

    # Colours to use for frequency plots
    colours = ["b", "g", "r", "c", "k"]
    frequencies = ["10Hz", "100Hz", "1000Hz", "10000Hz", "100000Hz"]

    # Assign a colour to each frequency band, process and plot data
    for jitter_data, colour, freq in zip(raw_jitter_data, colours, frequencies):

        if np.size(jitter_data) == data_size:
            pass
        else:
            print("Size of Frequency data: {}".format(data_size))
            print("Size of Jitter data: {}".format(np.size(jitter_data)))
            raise TypeError

        # Create empty numpy array equal to size of frequency values used in test to store plot data
        unsorted_data = np.empty((data_size, 2))

        # Store the test data in empty numpy array
        unsorted_data[:, 0] = freq_data[0:]
        unsorted_data[:, 1] = jitter_data[0:]
        unsorted_data.flatten()

        # Sort the test data numerically by frequency
        sorted_data = sorted(unsorted_data, key=lambda elem: elem[0])

        # Concatenate sorted data into numpy array
        data_set = np.empty((data_size, 2))
        for i in range(0, data_size):
            data_set[i] = sorted_data[i]

        # Split sorted test data into x / y numpy array
        plot_freq = np.empty(data_size)
        plot_jitter = np.empty(data_size)

        # Dump this data to a file
        if dumpcsv:
            timestamp = datetime.datetime.now().strftime("%b%d%Y-%H%M%S")
            np.savetxt(f"data_{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}_{timestamp}.txt", data_set)

        for i in range(0, data_size):
            plot_freq[i] = data_set[i, 0]
            plot_jitter[i] = data_set[i, 1]

        # Plot the x / y numpy arrays
        plot.plot(plot_freq, plot_jitter, colour + "-", label=freq, solid_capstyle="round")

    plt.legend(loc="upper left")
    return plot


if __name__ == "__main__":
    arguments = docopt(__doc__)

    with make_qx(arguments.get("GENERATOR_HOSTNAME")) as generator_qx, make_qx(arguments.get("ANALYSER_HOSTNAME")) as analyser_qx:
        number_of_plots = arguments["--plots"]
        jitter_amp = arguments["--amplitude"]
        patho = arguments["--pathological"]
        dumpcsv = arguments["--dumpcsv"]

        generator_qx.io.sdi_output_source = SDIIOType.BNC
        analyser_qx.io.sdi_input_source = SDIIOType.BNC

        standards_to_use = [
            ("1920x1080p24", "YCbCr:422:10", "1.5G_HLG_Rec.2020", "75% Bars"),
            ("1920x1080p59.94", "YCbCr:422:10", "3G_A_HLG_Rec.2020", "75% Bars"),
            ("4096x2160p25", "YCbCr:422:10", "6G_2-SI_HLG_Rec.2020", "75% Bars"),
            ("4096x2160p60", "YCbCr:422:10", "12G_2-SI_HLG_Rec.2020", "75% Bars")
        ]

        # If the analyser and generator Qxs are not in SDI Stress mode, exit
        if not generator_qx.query_capability(OperationMode.SDI_STRESS) or not analyser_qx.query_capability(OperationMode.SDI_STRESS):
            print("Error: Both analyser and generator must be in a mode that provides SDI Stress Toolkit instruments.")
            exit(255)

        # Create new figure
        fig = plt.figure(figsize=(15, 8), dpi=300, frameon=False, facecolor='white')

        i = 1
        for standard in standards_to_use:
            time.sleep(4)

            # Generate current standard on generator
            if not patho:
                generator_qx.generator.set_generator(standard[0], standard[1], standard[2], standard[3])
            else:
                generator_qx.generator.set_generator(standard[0], standard[1], standard[2], standard[3], pathological={"type": "CheckField", "pairs": 8192})

            time.sleep(5)

            if not analyser_qx.analyser.expected_video_analyser(standard[0], standard[1], standard[2]):
                print("Error when setting video standard... retrying")
                time.sleep(3)
                generator_qx.generator.set_generator(standard[0], standard[1], standard[2], standard[3])

            time.sleep(2)

            # Create a subplot inside the figure for the current data rate
            fig.add_subplot(2, 2, i)

            # Set x axis to log scale
            plt.xscale("log")

            # Set y axis limit to 0.8 UI
            plt.ylim(0, 0.8)

            # Get the current standard being analysed
            current_standard = "_".join(i for i in standard)
            print("Current standard is: {}".format(current_standard))

            # Draw axis labels
            plt.title(current_standard)
            plt.text(10, 0.85, "Jitter Amplitude: {}UI".format(jitter_amp))
            plt.xlabel("Frequency of jitter insertion")
            plt.ylabel("Jitter UI reading")

            # Display grid lines on subplot
            plt.grid(True)

            # Run jitter frequency step through and collect data
            raw_freq_data, raw_jitter_data = _step_through_jitter_frequency(float(jitter_amp), int(number_of_plots))

            # Plot the data to current subplot
            plt = _plot_jitter_ui(plt, raw_freq_data, raw_jitter_data, dumpcsv)

            # Increase plot index
            i += 1

        plt.tight_layout()
        generator_info = generator_qx.about
        analyser_info = analyser_qx.about
        timestamp = datetime.datetime.now().strftime("%b%d%Y-%H%M%S")
        fig.savefig(f'jitter_insertion_{analyser_info["Software_version"]}-{analyser_info["Build_number"]}_{analyser_info["FPGA_version"]}_{str(jitter_amp)}UI_{timestamp}.pdf')
