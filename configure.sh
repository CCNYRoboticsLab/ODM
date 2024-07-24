#!/bin/bash

# Ensure the DEBIAN_FRONTEND environment variable is set for apt-get calls
APT_GET="env DEBIAN_FRONTEND=noninteractive $(command -v apt-get)"

check_version() {
    UBUNTU_VERSION=$(lsb_release -r)
    case "$UBUNTU_VERSION" in
    *"20.04"* | *"21.04"*)
        echo "Ubuntu: $UBUNTU_VERSION, good!"
        ;;
    *"18.04"* | *"16.04"*)
        echo "ODM 2.1 has upgraded to Ubuntu 21.04, but you're on $UBUNTU_VERSION"
        echo "* The last version of ODM that supports Ubuntu 16.04 is v1.0.2."
        echo "* The last version of ODM that supports Ubuntu 18.04 is v2.0.0."
        echo "We recommend you to upgrade, or better yet, use docker."
        exit 1
        ;;
    *)
        echo "You are not on Ubuntu 21.04 (detected: $UBUNTU_VERSION)"
        echo "It might be possible to run ODM on a newer version of Ubuntu, however, you cannot rely on this script."
        exit 1
        ;;
    esac
}

if [[ $2 =~ ^[0-9]+$ ]]; then
    processes=$2
else
    processes=$(nproc)
fi

ensure_prereqs() {
    set -e
    export DEBIAN_FRONTEND=noninteractive

    if ! command -v sudo &>/dev/null; then
        # apt-key del "7fa2af80" &&
        #     export this_distro="$(cat /etc/os-release | grep '^ID=' | awk -F'=' '{print $2}')" &&
        #     export this_version="$(cat /etc/os-release | grep '^VERSION_ID=' | awk -F'=' '{print $2}' | sed 's/[^0-9]*//g')" &&
        #     apt-key adv --fetch-keys "https://developer.download.nvidia.com/compute/cuda/repos/${this_distro}${this_version}/x86_64/3bf863cc.pub"

        echo "Installing sudo"
        $APT_GET update
        $APT_GET install -y -qq --no-install-recommends sudo
    else
        sudo "$APT_GET" update
    fi

    if ! command -v lsb_release &>/dev/null; then
        echo "Installing lsb_release"
        sudo $APT_GET install -y -qq --no-install-recommends lsb-release
    fi

    if ! command -v pkg-config &>/dev/null; then
        echo "Installing pkg-config"
        sudo $APT_GET install -y -qq --no-install-recommends pkg-config
    fi

    echo "Installing tzdata"
    sudo $APT_GET install -y -qq tzdata

    echo "Installing exiftool"
    sudo $APT_GET install -y -qq libimage-exiftool-perl

    UBUNTU_VERSION=$(lsb_release -r)
    if [[ "$UBUNTU_VERSION" == *"20.04"* ]]; then
        echo "Enabling PPA for Ubuntu GIS"
        sudo $APT_GET install -y -qq --no-install-recommends software-properties-common
        sudo add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable
        sudo $APT_GET update
    fi

    echo "Install wget"
    sudo apt update              # Update the package list
    sudo apt install -y -qq wget # Install wget

    # echo "Remove the old key"
    # sudo rm /etc/apt/trusted.gpg.d/kitware.gpg

    # echo "Add the Kitware repository on Ubuntu 20.04 is to install the kitware-archive-keyring package"
    # sudo apt-add-repository "deb https://apt.kitware.com/ubuntu/ $(lsb_release -cs) main"
    # sudo apt update
    # sudo apt install kitware-archive-keyring

    echo "Updating cmake"
    sudo apt remove --purge --auto-remove cmake
    sudo apt update && sudo apt install -y -qq software-properties-common lsb-release && sudo apt clean all
    # wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | gpg --dearmor - | sudo tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null
    # # Add Repository to Sources List
    # echo "deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu focal main" | sudo tee /etc/apt/sources.list.d/kitware.list

    # sudo apt-key adv --fetch-keys https://apt.kitware.com/keys/kitware-archive-latest.asc
    # sudo apt-key list | grep 1A127079A92F09ED

    # sudo apt-add-repository "deb https://apt.kitware.com/ubuntu/ $(lsb_release -cs) main"
    sudo apt update
    sudo apt install -y -qq cmake
    apt-get install -y -qq python3-opencv

    echo "Installing Python PIP"
    sudo $APT_GET install -y -qq --no-install-recommends \
        python3-pip \
        python3-setuptools
    sudo pip3 install -U pip
    sudo pip3 install -U shyaml
}

# Save all dependencies in snapcraft.yaml to maintain a single source of truth.
# Maintaining multiple lists will otherwise be painful.
installdepsfromsnapcraft() {
    section="$2"
    case "$1" in
    build) key=build-packages ;;
    runtime) key=stage-packages ;;
    *) key=build-packages ;; # shouldn't be needed, but it's here just in case
    esac

    UBUNTU_VERSION=$(lsb_release -r)
    SNAPCRAFT_FILE="snapcraft.yaml"
    if [[ "$UBUNTU_VERSION" == *"21.04"* ]]; then
        SNAPCRAFT_FILE="snapcraft21.yaml"
    fi

    cat snap/$SNAPCRAFT_FILE |
        shyaml get-values-0 parts."$section".$key |
        xargs -0 sudo $APT_GET install -y -qq --no-install-recommends
}

installruntimedepsonly() {
    echo "Installing runtime dependencies"
    ensure_prereqs
    check_version

    echo "Installing Required Requisites"
    installdepsfromsnapcraft runtime prereqs
    echo "Installing OpenCV Dependencies"
    installdepsfromsnapcraft runtime opencv
    echo "Installing OpenSfM Dependencies"
    installdepsfromsnapcraft runtime opensfm
    echo "Installing OpenMVS Dependencies"
    installdepsfromsnapcraft runtime openmvs
}

installreqs() {
    cd /code

    ## Set up library paths
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$RUNPATH/SuperBuild/install/lib

    ## Before installing
    echo "Updating the system"
    ensure_prereqs
    check_version

    echo "Installing Required Requisites"
    installdepsfromsnapcraft build prereqs
    echo "Installing OpenCV Dependencies"
    installdepsfromsnapcraft build opencv
    echo "Installing OpenSfM Dependencies"
    installdepsfromsnapcraft build opensfm
    echo "Installing OpenMVS Dependencies"
    installdepsfromsnapcraft build openmvs

    set -e

    # edt requires numpy to build
    pip install --ignore-installed numpy==1.23.1
    pip install --ignore-installed -r requirements.txt
    #if [ ! -z "$GPU_INSTALL" ]; then
    #fi
    set +e

    installNodeODM
    apt-get install -y -qq python3-opencv
}

installNodeODM() {
    #!/bin/bash
    set -e
    # Install dependencies
    sudo apt-get update
    apt-get install -y curl gpg-agent ca-certificates
    curl --silent --location https://deb.nodesource.com/setup_14.x | bash -
    apt-get install -y nodejs
    npm --version
    apt install -y unzip p7zip-full
    sudo apt-get install -y git python3-gdal unzip libvips
    # sudo apt install -y -qq npm
    npm install -g nodemon
    ln -s /code/SuperBuild/install/bin/untwine /usr/bin/untwine &&
        ln -s /code/SuperBuild/install/bin/entwine /usr/bin/entwine &&
        ln -s /code/SuperBuild/install/bin/pdal /usr/bin/pdal

    # Create installation directory
    cd /code
    git config --global --add safe.directory /code
    git submodule add https://github.com/CCNYRoboticsLab/NodeODM.git
    # sudo mkdir -p /var/www/NodeODM
    sudo chown -R "$USER":"$USER" /code/NodeODM
    cd /code/NodeODM

    # Clone NodeODM repository
    # git clone https://github.com/OpenDroneMap/NodeODM.git

    # Install Node.js dependencies
    # cd NodeODM
    npm install --production && mkdir -p tmp

    # Create symbolic link for easier access (optional)
    # sudo ln -s /var/www/NodeODM/webodm /var/www/html/webodm

    # Configure NodeODM (if needed)
    # Edit the settings.yaml file in /var/www/NodeODM/config

    # Start NodeODM
    # npm start
    # node index.js
}

install() {
    installreqs

    # if [ ! -z "$PORTABLE_INSTALL" ]; then
    #     echo "Replacing g++ and gcc with our scripts for portability..."
    #     if [ ! -e /usr/bin/gcc_real ]; then
    #         sudo mv -v /usr/bin/gcc /usr/bin/gcc_real
    #         sudo cp -v ./docker/gcc /usr/bin/gcc
    #     fi
    #     if [ ! -e /usr/bin/g++_real ]; then
    #         sudo mv -v /usr/bin/g++ /usr/bin/g++_real
    #         sudo cp -v ./docker/g++ /usr/bin/g++
    #     fi
    # fi

    set -eo pipefail

    echo "Compiling SuperBuild"
    cd "${RUNPATH}"/SuperBuild
    mkdir -p build && cd build
    cmake .. && make -j"$processes"

    echo "Configuration Finished"
}

uninstall() {
    # check_version

    echo "Removing SuperBuild and build directories"
    mkdir -p "${RUNPATH}/SuperBuild/build/uninstalled"
    # cd "${RUNPATH}"/SuperBuild
    # rm -rfv build src download install
    # cd ../
    # rm -rfv build
}

reinstall() {
    # check_version

    echo "Reinstalling ODM modules"
    uninstall
    install
}

clean() {
    rm -rf \
        "${RUNPATH}"/SuperBuild/build \
        "${RUNPATH}"/SuperBuild/download \
        "${RUNPATH}"/SuperBuild/src

    # find in /code and delete static libraries and intermediate object files
    find "${RUNPATH}" -type f -name "*.a" -delete -or -type f -name "*.o" -delete
}

usage() {
    echo "Usage:"
    echo "bash configure.sh <install|update|uninstall|installreqs|help> [nproc]"
    echo "Subcommands:"
    echo "  install"
    echo "    Installs all dependencies and modules for running OpenDroneMap"
    echo "  installruntimedepsonly"
    echo "    Installs *only* the runtime libraries (used by docker builds). To build from source, use the 'install' command."
    echo "  reinstall"
    echo "    Removes SuperBuild and build modules, then re-installs them. Note this does not update OpenDroneMap to the latest version. "
    echo "  uninstall"
    echo "    Removes SuperBuild and build modules. Does not uninstall dependencies"
    echo "  installreqs"
    echo "    Only installs the requirements (does not build SuperBuild)"
    echo "  clean"
    echo "    Cleans the SuperBuild directory by removing temporary files. "
    echo "  help"
    echo "    Displays this message"
    echo "[nproc] is an optional argument that can set the number of processes for the make -j tag. By default it uses $(nproc)"
}

if [[ $1 =~ ^(install|installruntimedepsonly|reinstall|uninstall|installreqs|clean)$ ]]; then
    RUNPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    "$1"
else
    echo "Invalid instructions." >&2
    usage
    exit 1
fi
