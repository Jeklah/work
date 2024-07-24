#!/bin/bash
set -e

logfilename=$2
export TEST_QX=$1
export GENERATOR_QX=$1 
export ANALYSER_QX=$1
export AUTOLIB_LOG_FILENAME="${logfilename}.log"

pytest -ra -vvvv -s -l --junitxml="${logfilename}.junit.xml" "${@:3}" | tee "${logfilename}.pytest_output"

