#!/bin/bash
python3 -m pytest -ra -vvvv -s -l -m "not requires_device" --junitxml="unit_tests.junit.xml" autolib

