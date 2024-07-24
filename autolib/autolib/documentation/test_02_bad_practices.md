# Examples

## test_02_bad_practices.py
This test contains several examples of common bad practices when writing unattended automated tests that are to be run
by a CI server such as Jenkins or GitLab. Please read the comments in the file. 

There are some areas that are not described in the source file:

### Slices and argument list unpacking
In Python lists, tuples, sets and strings are examples of iterables (when iterating over a string, each character is 
treated as an item). Python slices allow sub-ranges to be extracted with simple notation
(https://docs.python.org/3/library/functions.html#slice). This test contains a slice literal:

```python
    new_standard = standard[1:]

    qx_unit.generator.set_generator(*new_standard, "100% Bars")
```

The `standard` variable here is a tuple containing four pieces of information, the data rate (3G, 1.5G etc.),
the resolution / frame type and rate (e.g. 1920x1080p50), the pixel format (e.g. RGBA:444:10) and the colour gamut
(e.g. Rec 709).  

The Qx object contains a number of methods and properties. Much of the functionality of a Qx is broken up into 
categories implemented as objects which are in turn exposed by properties. Here the generator functions are implemented
in an object exposed by the `generator` property. This object has a method `set_generator` which configures the
signal generator. It takes four parameters, the first three are the same as the last four in `standard` and the 
last is the name of a test card. We use a slice to create a new tuple containing everything but the first item.

We can now unpack the tuple `new_standard` tuple to an argument list for `set_generator` using the `*` operator. For 
more information on unpacking argument lists, please see 
https://docs.python.org/3/tutorial/controlflow.html#tut-unpacking-arguments.

### assert
Other Python test runners such as `unittest` and `nose` provide developers with a selection of assertion functions
to test for equality of variables, or whether an expected excaption is raised etc. PyTest provides these for 
backward compatibility but also allows plain Python `assert` statements to be used. PyTest performs introspection to 
add additional functionality so there is no need to use the older specialised assertion functions.
 