# Examples

## test_01_minimal.py
Our first PyTest test module. This contains one PyTest-discoverable function which (again) creates a Qx object and
prints it's details to stdout which will be captured by PyTest. The test clearly defines it's

```python
"""\
Our first PyTest test module. This contains one PyTest-discoverable function which (again) creates a Qx object and
prints it's details to stdout which will be captured by PyTest. The test clearly defines it's purpose.
"""
```
According to the Python documentation, a docstring is defined as:

> A docstring is a string literal that occurs as the first statement in a module, function, class, or method 
> definition. Such a docstring becomes the __doc__ special attribute of that object.

Python then uses these `__doc__` attributes to provide online help (either through the help() function or through your
IDE). This docstring applies to the entire module. It should describe the purpose of the tests in the module (the suite).

```python
from pprint import pprint
from autolib.models.qxseries.qx import Qx
```
Next, we need to import the Qx into the current namespace. To subtly improve upon the hello_qx_world.py code, we'll use
Python's `pprint` module to pretty print the dictionary returned by the about property.

```python
def test_about():
    """
    Test that a Qx / Qxl is running and responding to REST calls.
    """
```
We want PyTest to find and run our code so we will need it to be implemented within a function with a name that meets
PyTest's discovery requirements (https://docs.pytest.org/en/reorganize-docs/new-docs/user/naming_conventions.html).
The first statement (technically an expression) following the function definition is a docstring. This should describe
the purpose of the test concisely and clearly.

```python
    qx = Qx(hostname="qx-020000.local")
    pprint(qx.about)
```
Finally, we explicitly construct a Qx object and use the imported `pprint` function to nicely format the printed output.

At first glance it's difficult to see how this is really of any use at all as a test. The final two lines initially
appear to do very little. However on closer inspection, if the test completes, we know that:

* The Qx is turned
* The Qx is responding the mDNS requests (the hostname domain is .local so Avahi on the Qx is running)
* The Qx is responding to REST requests on port 8080

It's arguable that this test has a purpose if run at the start of a test run. If this very quick executing test fails,
then there is little point in wasting resources running further test suites.

 
