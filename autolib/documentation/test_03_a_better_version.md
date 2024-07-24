# Examples

## test_03_a_better_version.py
The purpose of this example is to address each of the problems identified in test_02_bad_practices.py. Please read 
through the comments in the source file.

Some additional notes about the test implementation:

### Python function decorators
PyTest provides a number of decorators that can be applied to test functions and classes. While not needed for their
use, an understanding of what a decorator is in Python is useful. Python functions are first class objects which means
that they can be passed to functions as parameters and returned from functions. In it's simplest form, a function 
decorator is a function that takes a function as a parameter and returns a function. Decorators can provide an easy
way to add functionality to functions and classes. 

Here's an example:

```python
import time

def timeit(f):

    def timed(*args, **kwargs):

        ts = time.time()
        result = f(*args, **kwargs)
        te = time.time()

        print(f'func:{f.__name__} args:[{args}, {kwargs}] took: {te-ts} sec')
        return result

    return timed
```
The function timeit takes a single argument, a function object `f` and defines a new nested function `timed` which 
gets the current system time, calls the function `f` passing it the positional and keyword arguments passed to it and
then gets the time after this completes. Finally it prints a message showing the time taken to execute `f` and then
returns the result of the call to `f`.

This can now be used as a function decorator using the following syntax:

```python
@timeit
def some_function(delay):
    time.sleep(delay)
    return "Finished"
    
print(some_function(3))
```
The function `some_function` has the `timeit` decorator applied to it. When this code is run, the decorator effectively
replaces the some_function call with a call to timed which in turn calls some_function and returns it's result. When
run, this code prints:

```
func:some_function args:[(3,), {}] took: 3.015157699584961 sec
Finished
``` 
The PyTest decorators add functionality to your tests in a number of ways. The `mark` functions add attributes to your
functions so at discovery time they can be optionally run or skipped. The `mark.parametrize` decorator generates 
multiple new tests using a single test definition that takes parameters and sets of input parameters.  

This only scratches the surface of decorators. A great primer on decorators can be found at:
https://realpython.com/primer-on-python-decorators/ 

### Parameterised tests
Test functions and method can be parameterised and called with different input data. This is allows data driven tests
to be implemented. The `pytest.mark.parametrize` (note the misspelling) makes this trivial.

```python
@pytest.mark.parametrize('width,height', ((10,40), (15, 30)))
def test_area(width, height):
    """
    Check that the area covered by a given width and height is large enough
    """
    assert (width * height) >= 425    
```
The `parametrize` decorator takes a string parameter containing a comma separated list of parameter names and a tuple
of values (if the string contains a single name, this tuple contains the values to assign to that parameter, if it
contains multiple parameter names, it contains tuples containing the values to assign to the parameters). In the
example above test_area will be called twice. The first time it's run the `width` parameter will be assigned the value 
`10` and the `height` parameter will be assigned the value `40`. The second time, `width` will be `15`, `height` will 
be `30`.

In this example, the data set used is a tuple literal in the source code. This isn't ideal as to modify the tests being
run the source code to the test must be changed and committed to source control. The tuple parameter however can be:

The result of a function call:
```python
@pytest.mark.parametrize('width,height', generate_data())
def test_area(width, height):
    ...
```

Loaded from a CSV file:

> test_data.csv
> ```csv
> width,height
> 10,40
> 15,30
> 1,400
> 42,42
> 123,456
> 20,70
> ```


```python
import csv
import pytest


def params_from_csv(filename):
    """
    Return parameters suitable for pytest.mark.parametrize from a CSV file
    """
    param_names = ""
    param_sets = []
    with open(filename, "rt") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        headers_read = False
        for row in csv_reader:
            if headers_read:
                param_names = ",".join(row)
                headers_read = True
            else:
                param_sets.append((row[0], row[1]))

    return param_names, param_sets


@pytest.mark.parametrize(*params_from_csv("../examples/test_data.csv"))
def test_area(width, height):
    ...
```

Loaded from a database:
> NOTE: Python contains built in support for creating and manipulating SQLite databases.
>
> Database creation:
> ```python
> import sqlite3
> 
> def generate_test_data(database_name):
>     """
>     For the purposes of this example, we need a table containing width and height columns and some data.
>     """
>     with sqlite3.connect(database_name) as connection:
>         cursor = connection.cursor()
>         dimensions_sql = """
>         CREATE TABLE dimensions (
>             id integer PRIMARY KEY,
>             width integer NOT NULL,
>             height integer NOT NULL)"""
>         cursor.execute(dimensions_sql)
>         data_sql = "INSERT INTO dimensions (width, height) VALUES (?, ?)"
>         for dataset in (10,40), (15,35), (42, 42):
>             cursor.execute(data_sql, dataset)
> 
> if __name__ == "__main__":
>     generate_test_data("test_data.db")
> > ```

```python
import pytest
import sqlite3

def params_from_database(database_name):
    """
    Return parameters suitable for pytest.mark.parametrize from a SQLite3 database
    """
    param_names = "width,height"
    with sqlite3.connect(database_name) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT width, height FROM dimensions")
        param_sets = cursor.fetchall()
    return param_names, param_sets


@pytest.mark.parametrize(*params_from_database("test_data.db"))
def test_area(width, height):
    ...
```
