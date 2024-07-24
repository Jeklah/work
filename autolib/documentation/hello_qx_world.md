# Examples

## hello_qx_world.py
A basic Hello World example where we create a Qx object and discover its software version etc. Realistically if this
were run as a test, all it would tell us it that the Qx is available and its REST interface is enabled. 

> NOTE: PyTest would not recognise this file as a test for two reasons. Firstly the filename does not match the pattern 
> requirements to qualify for discovery 
> (https://docs.pytest.org/en/reorganize-docs/new-docs/user/naming_conventions.html) and all code exists at module 
> scope so there is not test function or class method to execute.

```python
from autolib.models.qxseries.qx import Qx
```
Once installed, the automation library is available through the autolib package (although the installed 
package name visible in the output from `pip freeze` is `phabrix_autolib`). All controller objects are found in a 
module in the autolib.models package. In this case we directly create a Qx object from autolib.models.qx. In 
future examples we'll see how it's preferable usually to use a factory method when creating Qx or QxL objects. This 
explicit constructor though is sometimes appropriate.

```python
test_qx = Qx("qx-020000.local")
```
The Qx constructor method (__init__) is passed a keyword parameter `hostname` with the hostname of the device to 
control. If this is unsuccessful an appropriate exception will be raised. In most cases the test runner should be left
to catch exceptions as they represent a non-recoverable error state which indicates test failure. 

```python
print(test_qx.about)
```
Finally we print the content of the Qx object's `about` property. This is a dictionary obtained by a REST call to the 
device specified in the constructor containing the details of the unit. 

> NOTE: Python properties appear as class members but when they are read it triggers a call to a method that returns a
> value and when they are assigned to a method is called that takes the value being assigned and performs some custom
> behaviour. More detail about properties can be found here:
> 
> https://docs.python.org/3/library/functions.html?highlight=property#property.

