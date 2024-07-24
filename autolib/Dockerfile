# Use an official minimal Debian based Python image as a base image - note the shell in Debian is /bin/bash
FROM python:3.8-slim-buster

# Install prerequisites required to build the Python packages installed below.
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    apt-get update && \
    apt-get install -y build-essential bash libfreetype6 libfreetype6-dev libpng-dev libffi-dev libssl-dev \
    libjpeg-dev git git-lfs iputils-ping avahi-utils sshpass gosu && \
    git lfs install

# Set the working directory to /autolib
WORKDIR /autolib

# Install any needed packages along with their dependencies
RUN python3 -m pip install --upgrade pip && \
    pip install wheel cython bpython ptpython && \
    pip install --pre --extra-index-url https://nexus.rnd.phabrix.com/repository/phabrix_pypi_dev/simple/ phabrix-autolib

COPY submodules/docker_tools/user_mapped_rootfs /
COPY rootfs /

WORKDIR "/work"
USER root
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
