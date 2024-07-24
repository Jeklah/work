# Examples

## test_04_another_example.py
One of the strengths of PyTest is the way that it implements test fixture set up and tear down. In addition to 
supporting the various `setUp()` and `tearDown()` functions and methods that unittest and nose use to execute code
before and after tests and suites, PyTest provides support for fixture functions created using the `pytest.fixture`
decorator function. Fixture functions are defined that set state and optionally return objects for use in test code. To
make a fixture available to a test you add the fixture name to the test's parameter list. For example:

```python
import pytest

@pytest.fixture
def my_fixture():
    return [1,2,3,4,5]

def test_something(my_fixture):
    assert isinstance(list, my_fixture) 
```
Here during PyTest will recognise `test_something` as a test. It then looks at the test parameters and will find 
`my_fixture` which is knows is a fixture function. In this example, the my_fixture function will be run at the start
of the test. Fixtures may be functions but they may also be generators.

### Python Generators
Python generator functions are a way of creating iterator objects. These are used throughout the language. For example 
the built in `range` function doesn't return a list of numbers, it returns an iterable object - an object that 
implements the iterator protocol which is used to provide a series of values to (for example) a for loop. Python 3's 
`range` function returns an iterator to avoid having to allocate memory for a complete list of results in one go. 
Iterator objects implement the dunder methods required by the iterator protocol `__next__()` and `__iter__()`.

To create a generator, the `yield` keyword is used in place of return. Yield causes the function to pause execution and
return to the calling function while storing it's state. 

```python
from typing import Generator

def squares_generator(start: int, stop: int) -> Generator[int, None, None]:
    """
    Generate the squares of a series of integers from start to stop (inclusive).
    :param start: integer start value (insclusive)
    :param stop: integer stop value (inclusive)
    """
    value = start
    while value <= stop:
        yield value * value
        value += 1

if __name__ == "__main__":
    for square in squares_generator(1, 20):
        print(square)    
```  
Here, `squares_generator` returns an iterator object that will yield a series of squares of numbers from `start` to 
`stop`. The body of the function contains a while loop that loops through the number sequence and each time round it
`yield`s the square of the number. Each time the for loop calls the generator, execution continues after the yield so 
`value` is incremented and then the while clause is evaluated again and then the next value is returned.

So how is this useful for making fixtures? If your fixture yields a value to the test code, PyTest knows that it's a
generator and calls `next()` on the fixture allowing execution to continue after the yield allowing you to write tear
down code which will be run when the test completes.

```python
import pytest
from autolib.factory import make_qx

@pytest.fixture
def my_test_qx():
    """
    Provide a Qx / QxL to the test with bouncing box disabled.
    """
    test_qx = make_qx(hostname='qx-020008.local')
    bbox_state = test_qx.generator.bouncing_box
    test_qx.generator.bouncing_box = False
    yield test_qx
    test_qx.generator.bouncing_box = bbox_state

def test_something(my_test_qx):
    # Test something!
    ...
```
The test fixture `my_test_qx` provides a Qx or QxL (the make_qx factory function has been used to return an appropriate
object for the type of device by asking it what it is) that has the bouncing box in the generator disabled. The 
fixture function creates the object, saves the current bouncing box state, turns it off and yields the object to the
test. Then when the test has completed, the code following the yield is run restoring the pre-test state of the 
bouncing box. The fixture then completes and exits.

### Fixture scope
In the previous examples, the fixture is run at the start of the test and then it's post-yield code is run at the end
of a test. This is the default behaviour. If the fixture were to generate data, obtain data from an external source 
(the internet, a file etc.) or perform some expensive computation, it's important that it be only run as few times as
required by the tests. To achieve this, fixtures may have a defined scope.

Scopes are covered in the PyTest documentation here 
https://docs.pytest.org/en/stable/fixture.html#scope-sharing-fixtures-across-classes-modules-packages-or-session) and 
this article is quite good also 
https://medium.com/better-programming/understand-5-scopes-of-pytest-fixtures-1b607b5c19ed.

The scope keyword argument to the `pytest.fixture` determines when a fixture is run (setup) and when the post-`yield`
code is run (teardown). PyTest provides five scopes: function, class, module, package, session. So far we have seen 
function scope. Here is a class scope example:

```python
import pytest


@pytest.fixture(scope="class")
def dummy_data(request):
    print("\nExecute / setup the fixture")
    yield None
    print("\nTearing down the fixture")


class TestClass1:
    def test_1(self, dummy_data):
        print("\ntest_1")

    def test_2(self, dummy_data):
        print("\ntest_2")


@pytest.mark.usefixtures("dummy_data")
class TestClass2:
    def test_3(self):
        print("\ntest_3")

    def test_4(self):
        print("\ntest_4")
```  

There are two classes in the module, each defining some test functions. With the scope set to `class` fixtures are 
run the first time they're referenced in a class method and torn down once all class methods have been run. Also notice
that fixtures can be applied to test method in two ways - either by putting the fixture name in the test method 
parameters on a test by test basis or using by using a pytest decorator to automatically apply the fixture to all the 
methods in a class.  

The output from the test run is:

```
❯ pytest -s examples/test3.py 
============================================================================================================ test session starts =============================================================================================================
platform linux -- Python 3.8.5, pytest-5.4.2, py-1.8.1, pluggy-0.13.1
rootdir: /home/duncanw/git/autolib/examples, inifile: pytest.ini
plugins: timeout-1.4.2
collected 4 items                                                                                                                                                                                                                            

examples/test3.py 
Execute / setup the fixture

test_1
.
test_2
.
Tearing down the fixture

Execute / setup the fixture

test_3
.
test_4
.
Tearing down the fixture

============================================================================================================= 4 passed in 0.01s ==============================================================================================================
```
With the scope set to `module` the output would be:

```
❯ pytest -s examples/test3.py 
============================================================================================================ test session starts =============================================================================================================
platform linux -- Python 3.8.5, pytest-5.4.2, py-1.8.1, pluggy-0.13.1
rootdir: /home/duncanw/git/autolib/examples, inifile: pytest.ini
plugins: timeout-1.4.2
collected 4 items                                                                                                                                                                                                                            

examples/test3.py 
Execute / setup the fixture

test_1
.
test_2
.
test_3
.
test_4
.
Tearing down the fixture

============================================================================================================= 4 passed in 0.01s ==============================================================================================================
```
Similarly, the `package` and `session` scopes allow the fixture to be set up and torn down at the start and end of a 
whole package or at the start and end of the entire test run. 