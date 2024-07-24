#!/bin/bash

set -e

logfilename=$2

export TEST_QX=$1
export GENERATOR_QX=$1 
export ANALYSER_QX=$1 

export AUTOLIB_LOG_FILENAME="${logfilename}_fundamental.log"
pytest -ra -vvvv -l --junitxml="${logfilename}_fundamental.junit.xml" -m 'smoke and fundamental and not slow' | tee "${logfilename}.fundamental.pytest_output"

export AUTOLIB_LOG_FILENAME="${logfilename}.log"
pytest -ra -vvvv -l --junitxml="${logfilename}.junit.xml" -m 'smoke and not fundamental and not slow' | tee "${logfilename}.pytest_output"
