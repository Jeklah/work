# Starting Out
Phabrix automation library provides classes for the control, configuration and inspection of devices so tests are not 
tied to any specific test runner framework. All examples in this documentation use PyTest (also the choice for the Qx
test suite). 

## A Basic Test
This is a bare bones example PyTest test:

```python
from autolib.factory import make_qx
from autolib.models.qxseries.qx import Qx

def test_qx_is_qx():
    device_hostname = "qx-020008"
    with make_qx(hostname=device_hostname) as qx:
        device_is_qx = isinstance(qx, Qx)
        assert device_is_qx, f'{device_hostname} is {type(qx)}'
```

Important elements to note here are:
 
* ...the `make_qx()` factory function that creates either a Qx object or q QxL object based on the type of unit that
  hostname refers to. This is part of the Phabrix automation library. 

* ...that the function definition is prepended by the word `test_`, this is a rule of 
PyTest so that upon initialisation this function is identified as a valid test (as per
http://docs.pytest.org/en/stable/goodpractices.html#conventions-for-python-test-discovery). This is a feature
of PyTest.

* ...the `assert` statement, this is essentially where the test is evaluated to provide
a Pass / Fail status, `assert` can be followed by any standard Python comparison to evaluate True or False.

Tests of a similar type should be grouped into a test suite, this is achieved by writing the test functions inside of a 
class which defines the area under test.

```python
class TestAncillaryLocations:

    def test_s352(self):
        # This test will validate the presence of a s352 packet for the current standard            
        ...
        
    def test_audio(self):
        # This test will validate the presence of audio anc data when valid, embedded audio is detected in the SDI 
        # stream
        ... 
```         
   
Grouping tests in this fashion can be useful when performing multiple tests within a common area. As with the test function
definitions, a TestSuite definition (class name) is also required to contain the word "test" or it will not be executed 
as a test.

Further examples can be found in the [`examples`](worked_examples.md) folder.
