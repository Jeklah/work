#!/bin/bash

USER_LOGIN=$(id -un)

setup_git_lfs()
{
    # Install the global git hooks for LFS
    # Ubuntu versions prior to 20.04 don't support skip-repo and complain when the command is run outside
    # of an active git repo. We'll create a dummy repo to stop the complaint for older Ubuntu versions
    pushd /tmp > /dev/null 2>&1
    git init -q dummyrepo
    cd dummyrepo
    git lfs install --skip-repo
    popd > /dev/null 2>&1
    rm -rf dummyrepo
}

# NOTE: Since we may be mapping the real user home directory, be careful with the git config as it may already
# be correctly configured

# Setup git name if it's not already setup
if [ -z "$(git config --global --get user.name)" ]
then
    if [ -n "${GIT_NAME}" ]
    then
        git config --global user.name "${GIT_NAME}"
    else
        git config --global user.name "${USER_LOGIN}"
    fi
fi

# Setup git email if it's not already setup
if [ -z "$(git config --global --get user.email)" ]
then
    if [ -n "${GIT_EMAIL}" ]
    then
        git config --global user.email "${GIT_EMAIL}"
    else
        git config --global user.email "${USER_LOGIN}@phabrix.com"
    fi
fi

# Add everything as a safe directory (if not already added)
if ! git config --global --get safe.directory | grep -E "^\*$" > /dev/null
then
    # Don't bomb out when we come across differing ownership as we expect this with gitlab
    git config --global --add safe.directory '*'
fi
setup_git_lfs

CMD=$@
echo "Entrypoint command is: ${CMD}"

# We need to work around a nasty gitlab bug where it passes in a multiline script in the form
# sh -c if [ something ]; then
# dosomething
# fi
# This breaks when using a custom entrypoint and is complained about by many here:
# https://gitlab.com/gitlab-org/gitlab-runner/-/issues/3622
# To work around it, we will re-quote the command wherever we see "sh -c somecmd" or "bash -c somecmd"
# We'll always use bash for execution - should be a fairly safe assumption for most systems

PATTERNS[0]="^[\ ]*sh[\ ]*-c"
PATTERNS[1]="^[\ ]*/bin/sh[\ ]*-c"
PATTERNS[2]="^[\ ]*bash[\ ]*-c"
PATTERNS[3]="^[\ ]*/bin/bash[\ ]*-c"

for (( i=0; i<${#PATTERNS[@]}; i++ ))
do
    p=${PATTERNS[$i]}
    if [[ "${CMD}" =~ $p ]]
    then
        MATCH=${BASH_REMATCH[0]}
        CMD=${CMD:${#MATCH}}
        echo "Workaround applied for faulty injected script"
        break
    fi
done

# Switch to the users home directory (same as /work)
cd

# Execute specified command
eval "$CMD"
