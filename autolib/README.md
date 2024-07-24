# Phabrix Automation Library Introduction

The Phabrix automation library is an automation library for configuring, controlling and inspecting the state of various
devices. The automation library is an ever expanding thing and will never be 'complete' however a serious effort has been
made to put in place [a design and guidelines for it's extension](documentation/design_rules.md).  

There are models for the following devices:

* Qx
* QxL
* Black Magic Hyperdeck Studio Pro

Additional convenience classes are provided to make the creation of functional tests easier. The ArtifactArchiveFolder
is one such example.

## Documentation

The online documentation for the system can be found at http://holly:8078/autolib/

## Using the automation library in a container (without installing anything!)

> The Phabrix automation library is packaged in a Python 3.8 based self contained container for use on any x86-64 Linux distribution.
> The container provides the most portable way of using the automation library. The unit test system pytest and
> it's prerequisites are included along with everything required to run test suites.
>
> **Note:** This is only supported in Linux at this time

The container is stored in a container registry on our internal Nexus repository. In order to use the container, it is
strongly recommended to use the Phabrix internal tool `docker_run.sh` which is available from 
https://gitlab.com/phabrix/rnd/docker_tools.

To start an autolib session using the latest released container image, use:

    docker_run.sh run -d autolib

Please note that currently this will create a container attached to an internal network with NAT so when accessing 
devices you cannot currently use the mDNS .local domain. Thanks to improvements in the Phabrix networks though it
should not be necessary any more to rely on mDNS. 

Your home folder will be mounted as /work. When the container is created, your user and group are registered in the
container to ensure that you have full read / write access to /work.

## Installing a release of the automation library from Nexus using pip

The automation library is also available as a standard Python package that can be installed using pip. Install autolib and all it's prerequisites using:

Linux Bash (Requires Python v3.8):

    python3 -m venv venv
    source venv/bin/activate
    pip install --pre --extra-index-url https://nexus.rnd.phabrix.com/repository/phabrix_pypi_release/simple/ phabrix-autolib

Windows cmd.exe (Requires Python v3.8):

    python -m venv venv
    venv\Scripts\activate
    pip install --pre --extra-index-url https://nexus.rnd.phabrix.com/repository/phabrix_pypi_release/simple/ phabrix-autolib
    
Once installed it is unnecessary to clone this repo to use autolib. For example, save this code to 'simple.py' file and run it:

```python
from autolib.factory import make_qx

qx = make_qx(hostname="qx-020001")
print(qx.about)
print(type(qx))
```

Then run this with:

    python simple.py

This creates a Qx or QxL object and prints basic information about the unit (software version, operating mode, 
hardware revisions etc.) and the type of object that make_qx created (Qx or QxL). 

## Installing from GitLab for development
When developing the framework, you can install the automation library from a clone of the repository using a special pip
option that instead of copying the files into the installed packages folder in the venv (as a regular install would)
instead tells Python's installation system to use the files directly from the repo.

> **Important:** This method of install is highly recommended when developing the automation library further as your
> changes will be immediately reflected in your venv.

Linux Bash (Requires Python v3.8 or higher):

    git clone git@gitlab.com:phabrix/rnd/autolib.git
    python3 -m venv venv
    source venv/bin/activate
    cd autolib
    python generate_setup.py > setup.py
    pip install -e .

Windows cmd.exe (Requires Python v3.8 or higher):

    git clone git@gitlab.com:phabrix/rnd/autolib.git
    python -m venv venv
    venv\Scripts\activate
    cd autolib
    python generate_setup.py > setup.py
    pip install -e .

To confirm installation has been successful, run the simple.py file described in the previous section.

## Installed Scripts
There are utility command line tools located in the `autolib/utils` directory. If installed using pip or the
container is being used, these tools will be available on the path. Over time more tools will be added to this folder.

### take_screenshot.py
Use this script to quickly take a screenshot of the current GUI of a specified unit and transfer the generated `.png` 
file from the unit to the current working directory. The script takes a single argument which is the target unit
hostname.

    Usage:
        take_screenshot.py HOSTNAME
        take_screenshot.py --help

### generate_standards_sheet.py
Use this script to query a Qx series device for details of all of the supported SDI generator standards and generate
a sortable Excel spreadsheet. Ensure that the device is in SDI mode before running the tool.

    Usage:
        generate_standards_sheet.py [--output=<filename>] HOSTNAME
        generate_standards_sheet.py --help

## Example uses of the system
The section [Starting out](documentation/basic_test.md) acts as a primer for creating your first test using PyTest and
the Phabrix automation library.

The [`examples` package](documentation/worked_examples.md) contains a number of example tests and code examples with comment 
based commentary that explains their function and purpose.
