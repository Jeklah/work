#!/bin/bash

set -e

__error_handler()
{
    local _retval=$?
    local _lineno=$1
    echo "ERROR: $0 failed at line $_lineno: $BASH_COMMAND"

    exit $_retval
}

trap '__error_handler $LINENO' ERR

export TERM=xterm-256color
bold=$(tput bold)
normal=$(tput sgr0)
error=${bold}$(tput setaf 1)

echo_bold() 
{
    echo "${bold}$*${normal}"
}

echo_error() 
{
    echo "${error}$*${normal}" >&2
}

# Declare associative array for options
declare -A OPTIONS

# Declare a list of image locations, in priority order
declare -a IMAGES

# Define new associative array that we'll use to de-duplicate any mappings. Key is the docker mount point, value
# is host_mount_point:docker_mount_point:ro_flag e.g. MAPPINGS["/docker/path"]="/host/path:/docker/path:ro"
declare -A MAPPINGS

IMAGE_VER="latest"
XSOCKET_DIR="/tmp/.X11-unix"
CMD="/bin/bash"
WORK_DIR="$HOME"
GIT_NAME="$(git config --global --get user.name)"
GIT_EMAIL="$(git config --global --get user.email)"
NEXUS_DOCKER_RELEASE_REPO="nexus.rnd.phabrix.com:5000"
NEXUS_DOCKER_DEV_REPO="nexus.rnd.phabrix.com:5001"
NEXUS_DOCKER_PHABRIX_READ_PASSWORD_BASE64="I3lZYXAySEUjRENeUlRFWDRKXzM="
NEXUS_DOCKER_PHABRIX_READ_PASSWORD=$(echo -n ${NEXUS_DOCKER_PHABRIX_READ_PASSWORD_BASE64} | base64 -d)
ENV_VARS="DISPLAY=${DISPLAY};USER_LOGIN=$(id -un);USER_ID=$(id -u);GROUP_ID=$(id -g);GIT_NAME=\"${GIT_NAME}\";GIT_EMAIL=\"${GIT_EMAIL}\""

main()
{
    parse_options "$@"
    handle_options
    setup_docker_image
    add_user_volume_mappings

    case "${COMMAND_NAME}" in
        "clean")
            docker_cleanall
            ;;
        "create")
            handle_docker_create
            ;;
        "exec")
            handle_docker_exec
            ;;
        "help")
            usage
            ;;
        "list")
            handle_docker_list
            ;;
        "run")
            handle_docker_run
            ;;
        *)
            exit_usererror "Unrecognized command '${COMMAND_NAME}'"
            exit 1
            ;;
    esac
}

parse_options() 
{
    # Action is always the first argument
    set_action $1

    if [ "$1" == "" ]
    then
        exit_usererror "You must specify a command"
    fi

    # Start getopt from the second arg (as first is action)
    shift 1

    while getopts "bc:d:e:hm:n:p:s:v:w:x:X:-:" OPT; do
        # Manage long options
        if [ "$OPT" = "-" ]; 
        then
            OPT="${OPTARG%%=*}"         # extract long option name
            OPTARG="${OPTARG#"${OPT}"}" # extract long option argument
            OPTARG="${OPTARG#=}"        # Remove assigning '=' from long option
        fi

        case "${OPT}" in
            b | batch)
                OPTIONS[batch]=1
                ;;
            c | cmd)
                OPTIONS[cmd]="${OPTARG}"
                ;;
            d | image)
                OPTIONS[image]="${OPTARG}"
                ;;
            e | env-vars)
                OPTIONS[env_vars]="${OPTARG}"
                ;;
            m | map-locations)
                OPTIONS[map_locations]="${OPTARG}"
                ;;
            n | name)
                OPTIONS[name]="${OPTARG}"
                ;;
            p | docker-path)
                OPTIONS[docker_path]="${OPTARG}"
                ;;
            s | ssh-keys-dir)
                OPTIONS[ssh_keys_dir]="${OPTARG}"
                ;;
            v | docker-image-ver)
                OPTIONS[docker_image_ver]="${OPTARG}"
                ;;
            w | work-dir)
                OPTIONS[work_dir]="${OPTARG}"
                ;;
            x | xauth-dir)
                OPTIONS[xauth_dir]="${OPTARG}"
                ;;
            X | xsocket-dir)
                OPTIONS[xsocket_dir]="${OPTARG}"
                ;;
            :)
                exit_usererror "Error: -${OPTARG} requires an argument."
                ;;
            *)
                exit_usererror "Unrecognized option '${OPT}'"
                ;;
        esac
    done
}

usage() 
{
    echo "Usage: $0 [ clean | create | exec | help | list | run] [-d DOCKER_IMAGE | -p DOCKER_PATH]"
    echo "Commands:"
    echo "  clean                               Clean all containers created by this script with your username"
    echo "  create                              Create a new persistent container with the specified creation parameters (see below) but don't run anything (use with--exec)"
    echo "  exec                                Execute a command in an existing container with the specified execution parameters (see below)"
    echo "  help                                Print this help"
    echo "  list                                Lists all containers created by this script with your username"
    echo "  run                                 Run a new container with the specified creation parameters (see below) and run the command specified by --cmd (or ${CMD})"
    echo
    echo "Mandatory create/exec/run parameters"
    echo "  -d, --image=DOCKER_IMAGE            Specifies the Docker Image to run. Value can be one of:"
    echo "                                      'qx'                    - loads qxsoftwarebuilder from Nexus for building Qx software"
    echo "                                      'yocto_dunfell'         - loads bspbuildcontainers/yocto_dunfell from Nexus for building the Yocto BSP"
    echo "                                      'windows_mxe'           - loads bspbuildcontainers/windows_mxe from Nexus for building MXE toolchains"
    echo "                                      'native_ubuntu_18_04'   - loads bspbuildcontainers/native_ubuntu_18_04 from Nexus for building native apps"
    echo "                                      '70pj_x86_bsp'          - loads 70pj_buildcontainers/70pj_x86_bsp from Nexus for building 70PJ x86 BSP"
    echo "                                      '70pj_versal_bsp'       - loads 70pj_buildcontainers/70pj_versal_bsp from Nexus for building 70PJ versal BSP"
    echo "                                      '70pj_ph091_fp'         - loads 70pj_buildcontainers/70pj_ph091_fp from Nexus for building 70PJ PH091 front panel"
    echo "                                      'awscdk'                - loads awscdkbuildcontainer from Nexus for building AWS CDK stacks"
    echo "  -p, --docker-path=DOCKER_PATH       Can be use instead of '-d' to specify a customer docker path e.g. 'phablab:5005/qxrnd/bspbuildcontainers/my_container_name'"
    echo "                                      If used with -d, the image path will be overidden but any additional docker options will be preserved"
    echo
    echo "Optional create/exec/run parameters"
    echo "  -n, --name=NAME                     Use a specific name for the container (enabling running of containers of the same type concurrently)"
    echo "  -v, --docker-image-ver=IMAGE_VER    Specify the docker image version to use (defaults to '${IMAGE_VER}')"
    echo
    echo "Optional Create/Run Parameters:"
    echo "  -e, --env-vars=ENV_VARS             Specifies a semicolon separated list of environment variables to map in the form key=value"
    echo "  -m, --map-locations=LOCATIONS       Specifies a semicolon separated list of locations to map in the form host:container[:ro] (overriding any defaults)"
    echo "                                      For Qx image, defaults to '/home/toolchains:/home/toolchains;/home/images:/home/images;/opt/phabrix:/opt/phabrix'"
    echo "  -s, --ssh-keys-dir=SSH_KEYS_DIR     Specify the directory to map to \$HOME/.ssh (only required if work dir is not already home dir)"
    echo "  -w, --work-dir=WORK_DIR             Specify the working directory that will be mapped to /work in the container (defaults to ${WORK_DIR})"
    echo "  -x, --xauth-dir=XAUTH_DIR           Specify the directory to map to \$HOME/.Xauthority (only required if work dir is not already home dir)"
    echo "  -X, --xsocket-dir=XSOCKET_DIR       Specify the directory to map to /tmp/.X11-unix (defaults to '${XSOCKET_DIR_DEFAULT}')"
    echo
    echo "Optional Exec/Run Parameters:"
    echo "  -b, --batch                         Don't keep stdin open or allocate a tty (e.g. if executing something that isn't a terminal)"
    echo "  -c, --cmd=CMD                       Specify the command to execute (use with --exec/--run) (defaults to '${CMD}')"
    echo
    echo "Example usage with run"
    echo "  $0 run -d qx -n mycustomname        # Runs a new container with the name 'mycustomname' and the default command (normally /bin/bash)"
    echo "  $0 run -d qx -n mycustomname  -b -c 'echo Hello World'      # Runs a new container with the name 'mycustomname' with a custom command"
    echo
    echo "Example usage with create/exec:"
    echo "  $0 create -d qx -n mycustomname     # Creates a new container with the name 'mycustomname'"
    echo "  $0 exec -d qx -n mycustomname       # Executes the container with the name 'mycustomname' with the default command (normally /bin/bash)"
    echo "  $0 exec -d qx -n mycustomname -b -c 'echo Hello World'      # Executes the container with the name 'mycustomname' with a custom command"
    echo
    echo "Other example usage"
    echo "  $0 list                             # Show all my containers"
    echo "  $0 clean                            # Clean all my containers"

}

exit_usererror() 
{
    local message=$1
    if [ -n "${message}" ]
    then
        echo_error "${message}"
    fi
    echo
    usage 1>&2
    exit 1
}

handle_options() 
{
    local valid_options

    # Make sure we have a valid top level action to run
    if [ -z "${COMMAND_NAME}" ]
    then
        exit_usererror "You must specify one of --clean | --create | --exec | --list | --run"
    fi
    case "${COMMAND_NAME}" in
        clean)
            valid_options=""
            ;;
        create)
            valid_options="cmd image env_vars map_locations name docker_path ssh_keys_dir docker_image_ver work_dir xauth_dir xsocket_dir"
            ;;
        exec)
            valid_options="batch cmd image name docker_path docker_image_ver"
            ;;
        list)
            valid_options=""
            ;;
        run)
            valid_options="batch cmd image env_vars map_locations name docker_path ssh_keys_dir docker_image_ver work_dir xauth_dir xsocket_dir"
            ;;
    esac

    validate_options "${valid_options}"

    # Make sure we have something to execute
    if [ "${COMMAND_NAME}" == "run" ] || [ "${COMMAND_NAME}" == "exec" ] || [ "${COMMAND_NAME}" == "create" ]
    then
        if [ -z "${OPTIONS[image]}" ] && [ -z "${OPTIONS[docker_path]}" ]
        then
            exit_usererror "You must specify a Docker Image (-d) or a Docker Path (-p)"
        fi
    fi

    # Setup image version
    if [ -n "${OPTIONS[docker_image_ver]}" ]
    then
        IMAGE_VER="${OPTIONS[docker_image_ver]}"
    fi

    # Setup command
    if [ -n "${OPTIONS[cmd]}" ]
    then
        CMD="${OPTIONS[cmd]}"
    fi

    setup_work_dir

    if [ -n "${OPTIONS[ssh_keys_dir]}" ]
    then
        SSH_KEYS_DIR="${OPTIONS[ssh_keys_dir]}"
    fi

    if [ -n "${OPTIONS[xauth_dir]}" ]
    then
        XAUTH_DIR="${OPTIONS[xauth_dir]}"
    fi

    if [ -n "${OPTIONS[xsocket_dir]}" ]
    then
        XSOCKET_DIR="${OPTIONS[xsocket_dir]}"
    fi

    if [ -n "${OPTIONS[env_vars]}" ]
    then
        ENV_VARS+=";${OPTIONS[env_vars]}"
    fi
}

set_action()
{
    local action=$1

    COMMAND_NAME=${action}
}

validate_options()
{
    local valid_options="$1"
    local key
    # Check valid options for each action
    for key in "${!OPTIONS[@]}"
    do
        local valid=0
        # Check if key is in valid_options (don't quote this as it's a list!)
        for opt in ${valid_options}
        do
            if [ "${opt}" == "${key}" ]
            then
                valid=1
            fi
        done
        if [ ${valid} -ne 1 ]
        then
            exit_usererror "Option '--$key' is not valid for command ${COMMAND_NAME}"
        fi
    done
}

setup_work_dir()
{
    # Setupwork dir 
    if [ -n "${OPTIONS[work_dir]}" ]
    then
        WORK_DIR="${OPTIONS[work_dir]}"
    fi

    # Check we have a valid working directory
    if [ -z "${WORK_DIR}" ]
    then
        exit_usererror "You must specify a working directory"
    elif [ ! -d "${WORK_DIR}" ]
    then
        exit_usererror "Work directory does not exist!"
    fi
}

setup_docker_image()
{
    DOCKER_RUN_OPTS="--rm"
    DOCKER_CREATE_OPTS="" # Always keep active - will be hidden and not visible to user
    DOCKER_EXEC_OPTS=""
    CONTAINER_NAME=$(generate_container_name "${OPTIONS[image]}" "${OPTIONS[name]}")
    DOCKER_COMMON_CREATE_RUN_OPTS="--name ${CONTAINER_NAME} -l created_by_user=$(id -un)"

    if [ -z "${OPTIONS[batch]}" ]
    then
        DOCKER_COMMON_EXEC_RUN_OPTS+=" -it"
    fi

    if [ -n "${OPTIONS[image]}" ]
    then
        case ${OPTIONS[image]} in
            "qx")
                IMAGE_NAME="qxsoftwarebuilder"
                # Add Caps required for loop control
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --device /dev/loop-control"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --device /dev/mapper/control"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --cap-add=SYS_ADMIN"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --cap-add=MKNOD"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --security-opt apparmor:unconfined"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --device-cgroup-rule='b 7:* rmw'"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --privileged"

                # Map toolchains and images as read-only as only every deployed manually or by manual CI job
                MAPPINGS["/home/toolchains"]="/home/toolchains:/home/toolchains:ro"
                MAPPINGS["/home/images"]="/home/images:/home/images:ro"
                # Map /opt/phabrix as read-write as it can be written to if it's a local cache (if it's NFS it will be
                # automatically read-only anyway as the NFS share is read-only)
                MAPPINGS["/opt/phabrix"]="/opt/phabrix:/opt/phabrix"
                MAPPINGS["/opt/ccache_shared"]="/opt/ccache_shared:/opt/ccache_shared"
                ;;
            "yocto_dunfell")
                # Map /opt/phabrix as read-write as it can be written to if it's a local cache (if it's NFS it will be
                # automatically read-only anyway as the NFS share is read-only)
                MAPPINGS["/opt/phabrix"]="/opt/phabrix:/opt/phabrix"
                # Map /opt/yocto so we have a downloads mirror (managed by CI)
                MAPPINGS["/opt/yocto"]="/opt/yocto:/opt/yocto"
                # Map /home/yocto so we have a downloads cache
                MAPPINGS["/home/yocto"]="$HOME/yocto:/home/yocto"
                IMAGE_NAME="bspbuildcontainers/yocto_dunfell"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --cap-add=SYS_ADMIN"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --privileged"
                ;;
            "windows_mxe")
                IMAGE_NAME="bspbuildcontainers/windows_mxe"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --cap-add=SYS_ADMIN"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --privileged"
                ;;
            "native_ubuntu_18_04")
                IMAGE_NAME="bspbuildcontainers/native_ubuntu_18_04"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --cap-add=SYS_ADMIN"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --privileged"
                ;;
            "70pj_x86_bsp")
                # Map /opt/phabrix as read-write as it can be written to if it's a local cache (if it's NFS it will be
                # automatically read-only anyway as the NFS share is read-only)
                MAPPINGS["/opt/phabrix"]="/opt/phabrix:/opt/phabrix"
                # Map /opt/yocto so we have a downloads mirror (managed by CI)
                MAPPINGS["/opt/yocto"]="/opt/yocto:/opt/yocto"
                # Map /home/yocto so we have a downloads cache
                MAPPINGS["/home/yocto"]="$HOME/yocto:/home/yocto"
                IMAGE_NAME="70pj_buildcontainers/70pj_x86_bsp"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --cap-add=SYS_ADMIN"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --privileged"
                ;;
            "70pj_versal_bsp")
                # Map /opt/phabrix as read-write as it can be written to if it's a local cache (if it's NFS it will be
                # automatically read-only anyway as the NFS share is read-only)
                MAPPINGS["/opt/phabrix"]="/opt/phabrix:/opt/phabrix"
                # Map /opt/yocto so we have a downloads mirror (managed by CI)
                MAPPINGS["/opt/yocto"]="/opt/yocto:/opt/yocto"
                # Map /home/yocto so we have a downloads cache
                MAPPINGS["/home/yocto"]="$HOME/yocto:/home/yocto"
                IMAGE_NAME="70pj_buildcontainers/70pj_versal_bsp"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --cap-add=SYS_ADMIN"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --privileged"
                ;;
            "70pj_ph091_fp")
                # Map /opt/phabrix as read-write as it can be written to if it's a local cache (if it's NFS it will be
                # automatically read-only anyway as the NFS share is read-only)
                MAPPINGS["/opt/phabrix"]="/opt/phabrix:/opt/phabrix"
                IMAGE_NAME="70pj_buildcontainers/70pj_ph091_fp"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --cap-add=SYS_ADMIN"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --privileged"
                ;;
            "awscdk")
                # Map /opt/phabrix as read-write as it can be written to if it's a local cache (if it's NFS it will be
                # automatically read-only anyway as the NFS share is read-only)
                MAPPINGS["/opt/phabrix"]="/opt/phabrix:/opt/phabrix"
                IMAGE_NAME="awscdkbuildcontainer"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --cap-add=SYS_ADMIN"
                DOCKER_COMMON_CREATE_RUN_OPTS+=" --privileged"
                ;;
            *)
                exit_usererror "Unrecognized image '${OPTIONS[image]}'"
                ;;
        esac
    fi

    # Use specified docker image name, else use default Nexus release & dev images
    if [ -n "${OPTIONS[docker_path]}" ]
    then
        IMAGES[0]=${OPTIONS[docker_path]}
    else
        IMAGES[0]="${NEXUS_DOCKER_RELEASE_REPO}/${IMAGE_NAME}"
        IMAGES[1]="${NEXUS_DOCKER_DEV_REPO}/${IMAGE_NAME}"
    fi
}

generate_container_name() {
    local docker_image_name="$1"
    local custom_container_name="$2"
    if [ -z "${docker_image_name}" ]
    then
        docker_image_name="custom"
    fi
    echo -n "$(id -un).${docker_image_name}"
    if [ -n "${custom_container_name}" ]
    then
        echo -n ".${custom_container_name}"
    fi
}

add_user_volume_mappings()
{
    if [ -n "${OPTIONS[map_locations]}" ]
    then
        # Split the ";" separated list of requsted mappings and add them to our MAPPINGS array
        IFS=";"
        for map in ${OPTIONS[map_locations]}
        do
            local docker_mountpoint
            docker_mountpoint=$(echo "${map}" | cut -d":" -f2)
            MAPPINGS["${docker_mountpoint}"]="${map}"
        done
    fi

    if [ -n "${SSH_KEYS_DIR}" ]
    then
        MAPPINGS["/home/.ssh"]="${SSH_KEYS_DIR}:/home/.ssh:ro"
    fi

    if [ -n "${XAUTH_DIR}" ]
    then
        MAPPINGS["/home/.Xauthority"]="${XAUTH_DIR}:/home/.Xauthority"
    fi

    if [ -n "${XSOCKET_DIR}" ]
    then
        MAPPINGS["/tmp/.X11-unix"]="${XSOCKET_DIR}:/tmp/.X11-unix"
    fi

    if [ -n "${WORK_DIR}" ]
    then
        MAPPINGS["/work"]="${WORK_DIR}:/work"
    fi
}

docker_cleanall()
{
    echo "Removing containers owned by $(id -un)"
    CONTAINERS=$(docker ps -a --filter label="created_by_user=$(id -un)" | sed -e "1d" | cut -d' ' -f1)
    for i in ${CONTAINERS}
    do
	# Ignore any failures on the stop/rm as we want to continue regardless
        echo "Stopping container $i"
        docker stop -t 0 "$i" || true
        echo "Removing container $i"
        docker rm "$i" || true
    done
}

handle_docker_create()
{
    local image
    local cmd

    if container_exists "${CONTAINER_NAME}"
    then
        echo_error "The container you are trying to create already exists. You can remove it with the --clean option"
        exit 1
    fi

    echo "Creating '${OPTIONS[image]}'"
    echo

    print_docker_images
    setup_docker_volume_mappings
    setup_docker_env_vars
    find_docker_image

    if [ -z "${SELECTED_DOCKER_IMAGE}" ]
    then
        echo_error "Failed to find a docker image matching the requested name/version"
        exit 1
    fi

    cmd="docker create ${DOCKER_CREATE_OPTS} ${DOCKER_COMMON_CREATE_RUN_OPTS} ${DOCKER_ENV_OPTS} ${SELECTED_DOCKER_IMAGE} sleep infinity"

    echo "Creating new container... (${cmd})"
    echo "-----------"
    echo
    eval "${cmd}"
}

container_exists()
{
    local container=$1
    CONTAINERS=$(docker ps -a --filter label="created_by_user=$(id -un)" --filter name="^${container}\$" | sed -e "1d" | cut -d' ' -f1)
    if [ -n "${CONTAINERS}" ]
    then
        return 0
    fi
    return 1
}

find_docker_image()
{
    local actual_image

    # Iterate through prioritised list of images until we find one we can pull
    for i in "${!IMAGES[@]}"
    do
        # If there is a port marker (:) then we know a server was specified and we should login
        if [[ "${IMAGES[$i]}" == *":"* ]]
        then
            # Get everything before the first /
            local docker_server
            docker_server="${IMAGES[$i]%%/*}"
            if [ "${docker_server%%:*}" == "nexus.rnd.phabrix.com" ]
            then
                echo "Logging in to PHABRIX Nexus with read-only account"
                # Auto login with read-only account
                echo "${NEXUS_DOCKER_PHABRIX_READ_PASSWORD}" | docker login -u phabrix_read --password-stdin "${docker_server}"
            else
                echo "Logging in to '${docker_server}'"
                docker login "${docker_server}"
            fi
            echo "Trying to fetch image ${IMAGES[$i]}:${IMAGE_VER}..."
            if docker pull "${IMAGES[$i]}:${IMAGE_VER}"
            then
                actual_image="${IMAGES[$i]}:${IMAGE_VER}"
                break
            fi
        else
            actual_image="${IMAGES[0]}:${IMAGE_VER}"
        fi
    done

    if [ -z "${actual_image}" ]
    then
        return 1
    fi

    SELECTED_DOCKER_IMAGE="${actual_image}"
}

setup_docker_volume_mappings()
{
    echo " Volume Mapping:"
    for map in "${MAPPINGS[@]}"
    do
        # Add to docker run options
        DOCKER_COMMON_CREATE_RUN_OPTS+=" -v ${map}"

        # Print the mapping
        from=$(echo "${map}" | cut -d':' -f1)
        to=$(echo "${map}" | cut -d':' -f2)
        ro=$(echo "${map}" | cut -d':' -f3)
        if [ "${ro}x" != "x" ]
        then
            roflag="(ro)"
        else
            roflag=""
        fi
        echo "    ${from} -> ${to} ${roflag}"
    done
}

setup_docker_env_vars()
{
    echo " Environment Variables:"
    IFS=";"
    for e in ${ENV_VARS}
    do
        # Add to docker run options
        DOCKER_ENV_OPTS+=" --env $e"

        # Print the variable
        key=$(echo "$e" | cut -d'=' -f1)
        val=$(echo "$e" | cut -d'=' -f2)
        echo "    ${key} = ${val}"
    done
}

handle_docker_exec()
{
    local cmd
    if [ -z "${EXEC_ID}" ]
    then
        # Iterate through prioritised list of images until we find a matching one we can execute in
        for i in "${!IMAGES[@]}"
        do
            # Get id of first container matching image name
            EXEC_ID=$(docker ps -a --filter "ancestor=${IMAGES[$i]}:${IMAGE_VER}" --filter label="created_by_user=$(id -un)" --filter "name=^${CONTAINER_NAME}\$" | sed -n "2p" | cut -d' ' -f1)
            if [ -n "${EXEC_ID}" ]
            then
                break
            fi
        done
    fi

    if [ -z "${EXEC_ID}" ]
    then
        echo_error "Failed to find a docker container to execute - please check the image name or specify a specific container to use"
        exit 1
    fi

    # Make sure that the container is running - if it's not then start it (and just leave it running)
    if [ "$(docker container inspect -f '{{.State.Running}}' "${EXEC_ID}")" != "true" ]
    then 
        docker start "${EXEC_ID}" > /dev/null
    fi

    cmd="docker exec ${DOCKER_EXEC_OPTS} ${DOCKER_COMMON_EXEC_RUN_OPTS} ${DOCKER_ENV_OPTS} --user $(id -u):$(id -g) ${EXEC_ID} ${CMD}"
    echo
    echo "Executing in existing container... (${cmd})"
    echo " Command: ${CMD}"
    echo "-----------"
    echo
    eval "${cmd}"
}

handle_docker_list()
{
    echo "Listing containers owned by $(id -un)"
    docker ps -a --filter label="created_by_user=$(id -un)"
}

handle_docker_run()
{
    local image

    if container_exists "${CONTAINER_NAME}"
    then
        echo_error "The container you are trying to create already exists. You can remove it with the --clean option"
        exit 1
    fi

    echo
    echo "Running '${OPTIONS[image]}'"
    print_docker_images
    setup_docker_volume_mappings
    setup_docker_env_vars
    find_docker_image
    if [ -z "${SELECTED_DOCKER_IMAGE}" ]
    then
        echo_error "Failed to find a docker image matching the requested name/version"
        exit 1
    fi

    cmd="docker run ${DOCKER_RUN_OPTS} ${DOCKER_COMMON_CREATE_RUN_OPTS} ${DOCKER_COMMON_EXEC_RUN_OPTS} ${DOCKER_ENV_OPTS} ${SELECTED_DOCKER_IMAGE} ${CMD}"
    echo
    echo "Executing in new container... (${cmd})"
    echo " Command: ${CMD}"
    echo "-----------"
    echo
    eval "${cmd}"
}


print_docker_images()
{
    echo " Images:"
    for i in "${!IMAGES[@]}"
    do
        echo "   Image[$i]: ${IMAGES[$i]}:${IMAGE_VER}"
    done
}

main "$@"

