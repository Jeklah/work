#!/bin/bash

sphinx-apidoc -f -o built_documentation -e -F autolib autolib/models/arista.py autolib/models/emsfp.py autolib/models/jenkins.py autolib/models/serial.py
cp README.md built_documentation/introduction.md
cp apidoc_source/* built_documentation
cp documentation/* built_documentation
pushd built_documentation
make html
popd
