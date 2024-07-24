#!/bin/bash
set -e

logfilename=$2
export TEST_QX=$1
export GENERATOR_QX=$1 
export ANALYSER_QX=$1
export AUTOLIB_LOG_FILENAME="${logfilename}.log"

pytest -ra -vvvv -s -l --trace --capture=no --pdbcls pudb.debugger:Debugger --junitxml="${logfilename}.junit.xml" "${@:3}" 

