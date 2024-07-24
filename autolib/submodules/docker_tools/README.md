This repository contains common scripts and tools used to support Docker across PHABRIX.

# docker_run.sh
This helper script makes it easy to run the Docker containers used to build the Yocto BSP, MXE toolchain, native SDKs and Qx software. It provides flexibility to map SSH keys, X11 sessions etc so that you can effectively develop and build your software inside the container, knowing it will compile exactly the same way on any other build machine.

# user_mapped_rootfs
This rootfs contains the scripts necessary to map the host user into the container. Doing so ensures that the uid/gid of file ownership is properly preserved on mapped volumes, allowing the container to be used for development purposes. This rootfs should not contain product or BSP-specific implementations; where this is needed, a fork should be used, or an overlay applied.
