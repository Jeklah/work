#!/bin/bash

# Get details of current user (passed into docker) or otherwise default to values below
USER_ID=${USER_ID:-15000}
GROUP_ID=${GROUP_ID:-15000}
USER_LOGIN=${USER_LOGIN:-"builder"}

# Create a user matching the name/ids on the host system
groupadd -g ${GROUP_ID} ${USER_LOGIN}_grp
useradd --shell /bin/bash -u ${USER_ID} -g ${GROUP_ID} -o -c "${USER_LOGIN}" -p "" -d /home/${USER_LOGIN} ${USER_LOGIN}
# Create a bind mount so the user's home directory appears in the right place
mkdir -p /home/${USER_LOGIN}
mount --bind /work /home/${USER_LOGIN}
usermod -G sudo ${USER_LOGIN}
chown ${USER_LOGIN} /home

CUSTOM_CONTAINER_SETUP_SCRIPT="/usr/local/bin/containersetup.sh"
if [ -x ${CUSTOM_CONTAINER_SETUP_SCRIPT} ]
then
    ${CUSTOM_CONTAINER_SETUP_SCRIPT}
elif [ -f ${CUSTOM_CONTAINER_SETUP_SCRIPT} ]
then
    echo "ERROR: Custom container script exists, but is not executable - skipping"
fi

# Switch to user, setup user and execute command passed into docker
exec gosu ${USER_LOGIN} /usr/local/bin/setupandexecute.sh "$@"
