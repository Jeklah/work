# Automation library design principles

This is an automation library. It's purpose is to allow devices to be configured, controlled and inspected such that
tests can be written using it. It does not provide any kind of testing framework or test runner. The Qx test suite that
makes use of this library uses pytest as it's testing framework. This library is also used to make standalone apps that
are used by developers to aid in the exploratory testing of new functionality.

## Why do we need this?

### Don't Repeat Yourself!

To make an effective and relatively easy to maintain set of unattended self-assessing tests for the products we make 
could not easily be done through simple scripting and Rest API calls. For example, consider the basic operation of 
rebooting a test unit. You could simply SSH into the unit and execute 'reboot'. However, following that reboot how would 
you know when the test unit is completely ready to be interacted with? Using a sleep call is not appropriate for a 
number of reasons - did the unit actually reboot? Is the sleep duration suitable long to *guarantee* that the unit is 
ready but at the same time not so long as to waste time needlessly in a test? If the test reboots the unit several times 
this wasted time has a very negative impact on the test suite run time (and development time when performing test runs 
of the test).

In the Qx object there is a method 'reboot' which requests a reboot via SSH which initially waits until the device 
becomes unreachable then waits for a number of criteria to be met before continuing, timing out if the device doesn't
enter the expected states within an acceptable time. This is not something you would want to repeat in every test and
the precise criteria may differ between devices. This should be hidden from the test writer. This should be possible:

```python
from pprint import pprint
from autolib.factory import make_qx

qx = make_qx("qx-020000")
qx.reboot()
pprint(qx.about)
```

This short example reboots the Qx with hostname qx-020000 and then prints the content of the About details. To do this
without the automation library would require that the user write a reboot function that waits for the unit to be ready
(which is surprisingly tricky!) and then load an http client module and create a request to GET the /system/about 
endpoint from the device, handling any errors that may occur here. Here, it required three lines of code. 

Without the automation library:

```python
from paramiko import SSHClient, AutoAddPolicy

def reboot_and_wait(hostname: str, uname: str = 'root', pword: str = 'PragmaticPhantastic'):
    with SSHClient() as client:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(AutoAddPolicy())   
        client.connect(hostname, username=uname, password=pword)
        stdin, stdout, stderr = client.exec_command('reboot')
        [x.close() for x in (stdin, stdout, stderr)]
    
    # Ping periodically until the device becomes unavailable
    
    # Ping periodically until the device becomes available
    
    # Attempt SSH connection until success
    
    # Via SSH wait for all required processes to be available
    
    # Probe required ports until all available
    
    # Attempt Rest API call until available
    
    # ... etc.
```

And this would need to be written to work on all Qx series devices (the list of essential processes differs for one).
This and many other similar methods such as upgrade() (for upgrading the software version) are provided as methods for
DeviceControllers.

## Goals

The Phabrix automation library has grown from initial work to make the job of creating functional tests of equipment 
such as the Qx and QxL quicker and with the minimal of repetition. 

The library provides Python classes that allow users to easily configure, control and inspect devices and allow tests to
be then written using a suitable test framework (in our case pytest), command line apps can be quickly written and GUI 
apps (using PySide, wxPython etc.) or web apps (using Streamlit or NiceGUI etc) can be easily created.

The following are the design goals that should be considered when extending the automation library.

### Avoid repetition

The autolib library's primary goal is to make the job of writing tests that exercise device functionality easier and
with far less repetition. Ironically this paragraph is a repetition of previous section but this is critical to the 
design of the system. If while writing a test you have code that will prove useful in other tests, the automation 
library will act as a home to put this (possibly with some subtle redesign if necessary). The automation library is a
living development and will never be 'finished'. It will be extended all the time that new tests are being developed.

### Device-agnostic tests

As our product line has new variants added and as the abilities of the devices change over time we should have to only
rewrite tests directly affected by the changes. There should be no need to revisit everything, especially in a large 
suite of tests. Since the original test system code was written we now have two additional members of the Qx family. By
using the automation library we can write a test that will work on any variant (assuming the test is for a feature 
present on all variants). To give a concrete example of this, the QxL and Qx both have two media SFP interfaces however
they are named differently in both the user interface and (more importantly) the Rest API. Interface access via the
automation library is abstracted and this is handled automatically.

To ease the writing of tests, DeviceController instances (the abstract base class of all device controlling classes) are
created using factory methods. The `make_qx` factory method will return an appropriate DeviceController (Qx, QxL or QxP)
by querying the specified device to see what it is. In some situations this may be unnecessary (e.g. if you are writing
a test that tests a feature specific to that device only) so you are not prevented from instantiating a specific 
DeviceController class, but it is highly recommended that you use the factory functions.

### DeviceController methods - the three main types

#### Fundamentals
The DeviceController base class defines a set of methods that must be implemented in every DeviceController. These are
fundamental operations such as reboot, capability request methods, and methods that restore the device to a good known
'start state'.

#### Thin API wrappers
When wrapping Rest APIs (or other control protocols) the preferred approach is to write thin wrappers around the  
remote APIs (for example using the RestBoilerPlate metaclass) and then creating methods that use these to accomplish
a complete self-validating function. An example of this is the reboot mechanism in the Qx model which performs a 
reboot but then blocks while it waits for a number of conditions to be met before continuing (with a timeout that
if met will cause an appropriate exception to be thrown).

#### Convenience methods
It's often overly verbose to construct a dictionary to pass to the API wrapper methods every time. This usually leads
to code bloat. The convenience methods are there to provide a simpler interface to features. For example there are 
methods that simplify the output of the CRC analyser methods and perform some degree of processing on the data to return
it in a cleaner form to the calling code.

> It is expected over time that the convenience methods are one of the areas that will grow the most during the 
> ongoing development of the automation library. As tests are developed, we will increasingly see areas where code
> duplication is occurring.

### Capability requests

Originally when the Qx class was first added to the automation library tests would explicitly change the operation mode 
depending on the tests that were to be run (2022-6, SDI, SDI Stress and 2110). Then, the SDI Stress functionality was
merged into the SDI operation mode. Now tests would request a mode that potentially wasn't valid on newer software. 

To combat this by way of a general purpose mechanism, tests were changed to request capabilities rather than to select
specific modes. Now a test would request SDI capabilities and the Qx object would then work out what would be needed to
make that capability available. 

> This is an area that we will be revisiting as work is well underway to integrate all operation modes into one for
> 70PJ. This is potentially being backported to the Qx series too. To know how the capability resolver works at the 
> moment uses the software version number. This is not ideal and some design work is needed here. 

### Minimising test run durations

As previously mentioned, when automating devices as a part of a test it is bad practice to use sleep commands to wait
for a device to be in an expected state. Where possible, methods such as reboot, request_capability (more on this later)
etc. will block until the device is in the expected state. This blocking state will not be indefinite and there will be 
a timeout after which an appropriate exception is thrown. This helps to avoid needlessly waiting a 'safe' (i.e. long) 
amount of time for the device to be in an expected state. 

### Exceptions

Exceptions are an important part of Python. While similar to C++ exceptions, their use is far more common and the
automation library makes heavy use of them. Exceptions are used to indicate that an exceptional state has been reached
that is unexpected. When tests fail, uncaught exceptions filter down to the test runner (pytest) where they will form
part of the test failure report.

The automation system raises a variety of different Exception subclasses to indicate to the calling system that 
something is wrong. This also allows the calling code to catch and handle and / or ignore exceptions.

Automation library exceptions inherit from either CoreException (exceptions that are raised by core autolib code) or 
TestException (exceptions raised in test code - tests may implement subclasses of TestException). 

### "Block until ready"

The framework should perform all necessary checks to ensure that an operation has completed successfully before 
allowing the test to continue. For example, the update, reboot and mode switch methods of the Qx object block
execution until the operation has been successful or raising an appropriate exception in the event of failure or 
timeout. 

### Helper classes

Helper classes are available to make the writing of tests easier. An example would be the TestArchive class that 
acts as a bucket that test output files such as PNGs or CSV files etc. can be stored in such that they get ZIPped up
on test completion for archival by a CI system. 

### Readbility 
 
Test framework claases should allow tests to 'read' clearly. Their behaviour should be as clear as possible from the 
code. Test runners like pytest can extract information at the tests in a suite using their docstrings. These generally
describe the purpose of the test but the test code should describe how they work without the need for debuggers.

### Installation

The automation library should be easily installable either through `pip` from an internally hosted repository of 
Python software, usable as a Docker container (Linux only) or installable in source form from GitLab. 


## Test Writing Recommendations

* The automation library should be usable in any test framework (unittest, nose, pytest) but in no way tied any of them.
* The intent of tests must be documented in the test's docstrings such that it is possible to generate a human readable
  list of all tests that may be accessible by non-developers.

## Writing device controller classes
Control of devices is performed through DeviceController subclasses. The DeviceController interface is a very basic 
contract that provides a very small set of fundamental methods that must be implemented by all devices or services. 
These include a blocking method (with timeout) to restart the device, returning only when the device is ready to 
automate and a method that will set the device into a known good state

## Guidelines for extending the system

### All changes are to be made on story / subtask branches and reviewed
One of the problems with the automation library in it's early stages was that all changes were made on master with no 
review process. 

> **IMPORTANT:** *ALL* changes are to be made on `story` / `subtask` branches using the same branching rules as the
> Qx repo and may only be merged to `master` by the reviewer (who must not be the original developer). This is both to
> ensure quality / design direction but to foster discussion and to spread knowledge of the system.

### Version numbering
The Phabrix automation library will use Semantic Versioning for the built installable pip packages on GitLab. The rules 
must be followed as defined in http://semver.org. To summarise:

> Given a version number MAJOR.MINOR.PATCH, increment the:
> 
>     MAJOR version when you make incompatible API changes,
>     MINOR version when you add functionality in a backwards compatible manner, and
>     PATCH version when you make backwards compatible bug fixes.

Builds from GitLab will have the build number added to the end of the version number (MAJOR.MINOR.PATCH-build)

> IMPORTANT: For every merge of a story to master, the appropriate version number component(s) MUST be updated before
> merging. 

### Classes in the models package represent devices and their behaviours
A model in autolib is an object that represents a piece of equipment (e.g. Qx). They may be created explicitly (e.g. 
`Qx`) or via a factory method (e.g. `make_qx`)

### PEP8 rules should be adhered to
Python Enhancement Protocol 8 defines a code style standard that we should use. All Python IDEs provide linting support 
for this standard. This removes any ambiguity as to which style is 'correct'.

### Use layered public APIs
To avoid huge flat public APIs and make reuse and unit testing easier, models should be composed of loosely coupled 
sub-objects representing specific functionality exposed through properties. For example:

```python
# Favour
test_unit.generator.set_standard( ... )

# Over
test_unit.set_generator_standard( ... )
```

and:

```python
# Favour short meaningful method names in subobjects that group domain functionality...
test_unit.ip2022_6.request_mcast( ... )
test_unit.ip2110.request_mcast( ... )

# ...Over long method names where there is repetition of the domain at the start of the method name
test_unit.ip2022_6_request_mcast( ... )
test_unit.ip2110_request_mcast( ... )
```

### Create factory functions to instantiate device objects
To ensure that tests can be run over different models of a common family (e.g. Qx and QxL), models that are of the same 
family may be created using a factory method that determines the appropriate type by querying the device directly.
e.g. autolib.factory.make_qx will give you an instance of Qx or QxL based on the actual physical unit.

```python
# Favour this (test_unit will be the right type of object for 'qx-020008')
from autolib.factory import make_qx
test_unit = make_qx(hostname='qx-020008')

# Over (this assumes - potentially falsely that 'qx-020008' is a Qx)
from autolib.models.qxseries.qx import Qx
test_unit = Qx(hostname='qx-020008')
```

There is a factory for creating TestArchive objects too giving them a sensible ZIP filename based on time and test name:

```python
from pathlib import Path
from autolib.factory import make_artifact_archive

# The following will result in the creation of a ZIP file named:
#   <module_name>_<function_name>_<timestamp>.zip
# containing a file 'somefile.txt' with content 'Some data'
with make_artifact_archive('some_id', Path.home()) as archive:
    with open(Path(archive.folder) / 'somefile.txt', 'wt') as output_file:
        output_file.write("Some data")
```

This creates a temporary folder object `archive` whose `folder` attribute is a folder in which you can place your
artifacts. The above code creates a text file `somefile.txt` and writes "Some data" to it. Because both open() returns
a context manager and make_artifact_archive also returns a context manager, when the scopes end firstly the text file 
is closed. Then as the ArtifactArchive returned by make_artifact_archive goes out of scope the temporary folder is 
zipped up into a file in the target folder (here the user's home directory) and then the temporary folder is deleted.
    
### Exception types

#### CoreException 
Core device object methods that experience an error that prevent them providing a useful return code should raise an 
appropriate CoreException subclass to indicate to the calling code that an unrecoverable error is to terminate the test 
(e.g. QxException)

#### TestException
TestException provides a bass class to derive test-specific failure exceptions. These should only be used in tests and 
not in the core. They should be raised when unrecoverable failure conditions are met or a failure constitutes a failure 
of the test.

### When to create Properties in device classes
Model methods that get or set (through a single parameter) the state of a device attribute (e.g. bouncing box) should 
be implemented as Properties.

### External resources (RAII)
When writing code that uses an external resource such as a file or database, use the with statement or implement the 
context manager protocol methods (`__enter__()` and `__exit__()`) depending on the nature of the code.

```python
# Favour
with open("filename", "w") as data: <1>
    read_data = data.read()

# Over
data = open("filename", "e")
read_data = data.read()
data.close() <2>
```

<1> Using the with statement causes the file to be closed when it leaves scope.

<2> If the read() raises an exception, this close will not be called (though 
    file handles are closed when eventually garbage collected).

If you are writing an object that wraps calls to an external resource (like a class that accesses a database), ensure 
that both the context manager protocol methods (`__enter__` and `__exit__`) are implemented to allow the object to be 
used with the with statement freeing any held resources in `__exit__`. The `__del__` method for the object should also 
ensure that any held resources are freed when the object is garbage collected (remember that `__del__` is not the same 
as a destructor though as destructors are run straight away whereas the garbage collector will determine when the object 
is collected).

```python
class Database:
    def __init__(self):
        self._url = None
        self._db_open = False

    def open(self, url):
        self._url = url
        open_nosql_db(self._url)
        self._db_open = True

    def close(self)
        if self._db_open:
            close_nosql_db()
            self._db_open = False

    def __del__(self):  <1>
        self.close()

    def __enter__():  <2>
        return self

    def __exit__():  <3>
        self.close()
```
<1> `__del__` is called when an instance of Database is collected.

<2> `__enter__` is called by the with statement.

<3> `__exit__` is called when the with statement block ends

## Test design guidelines
### Write for unattended execution
If a test is to be run by CI it must be self validating (it must return Pass or Fail). It may optionally produce other 
test artifacts that will be stored for examination after the test run.

### Use appropriate logging
Tests should produce output that should aid in the diagnosis of failures. As a result, proper use of the logging class 
should be made and Exception failure messages should be clear and useful.

### Favour readable code over heavy commenting
Comments should only be used to express that that may not be easily expressed through the code.

### Test descriptions are mandatory
Every test class and test method / function MUST have a clear docstring that describes the test. These descriptions are 
extracted by various tools to make test reports readable and to make it easier to identify tests for given functional 
areas.

### PyTest marks
When using pytest, custom markers are used to allow better flexibility in the way we run test suites. They are the most 
beneficial when used very sparingly. There should be very strong reasons for adding new custom marks.

### Test parameterisation
If your test is iterative by nature (for example the test performs a certain operation for each supported generated 
video standard)

### Test suite Configuration
The autolib does not mandate any one configuration mechanism. Currently the Qx tests are configured through a small 
number of environment variables set by the user or by Jenkins when a test suite is run. This approach can become 
unwieldy if you have lots of configuration. Avoid the tendency to configure tests through static files (especially if 
store in Git). This approach makes it quite difficult to integrate the configuration in CI system. Alternatives include 
JSON documents stored on a NoSQL database such as CouchBase or MongoDB or JSON / YAML files generated by script code in
Jenkins.

### Persistent data between test runs
Currently, autolib neither mandates not provides any special functionality for storing data over subsequent test 
runs. To do so only really makes sense in a CI situation where the tests are run in the same environment each time. The 
Jenkins jUnit plugin stores test results from subsequent runs and graphs the failure count. If data from runs needs to 
be stored in a cumulative fashion, consider setting up a backed up database server for the task. Avoid files where 
possible as they need to be hosted someplace reliable and suitable for multi-user access.  

## Choice of pytest

Pytest is the current choice for writing tests as it has excellent community support and some very nice features 
including but not limited to:
 
* A flexible scoped fixtures mechanism for setup and teardown of devices.
* Test tagging for partial test suite runs
* Easy test parameterisation to reduce repetition and make data driven tests quicker to write. 
* Automatic test discovery (as tests and / or classes are added to the test package they will be run automatically by 
  pytest)
* jUnit format report output (consumable by Jenkins) 
* Plugins that provide useful features like automatic test failure if they exceed a specified execution time. 
* Test debugging using Python's pdb debugger and the ability to integrate with PDB GUIs.
* It's supported on several IDEs including Microsoft Visual Studio Code and PyCharm Community Edition. 
