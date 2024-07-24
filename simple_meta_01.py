#!/usr/bin/env python3

# Meta Programming Exercise
# Two step metaclass creation in Python 3.6
# Author: Arthur Bowers


class SimpleMeta(type):
    def __init__(cls, name, bases, nmspc):
        super(SimpleMeta, cls).__init__(name, bases, nmspc)
        cls.uses_metaclass = lambda self: "Yes!"


class SimpleClass(metaclass=SimpleMeta):
    __metaclass__ = SimpleMeta

    def foo(self):
        pass

    @staticmethod
    def bat():
        pass


def main():
    simple = SimpleClass()
    print([m for m in dir(simple) if not m.startswith('__')])
    # A new method has been injected by the metaclass:
    print(f'{simple.uses_metaclass()}')


if __name__ == '__main__':
    main()
