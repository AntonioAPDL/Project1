#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

# Function to print an error message and exit
function error_exit {
    echo "$1" 1>&2
    exit 1
}

# Step 1: Download and extract ECCODES source code
wget https://confluence.ecmwf.int/download/attachments/45757960/eccodes-2.26.0-Source.tar.gz || error_exit "Failed to download ECCODES"
tar -xvzf eccodes-2.26.0-Source.tar.gz || error_exit "Failed to extract ECCODES"
cd eccodes-2.26.0-Source || error_exit "Failed to enter ECCODES source directory"

# Step 2: Download, build, and install cmake locally
wget https://github.com/Kitware/CMake/releases/download/v3.21.1/cmake-3.21.1.tar.gz || error_exit "Failed to download cmake"
tar -xvzf cmake-3.21.1.tar.gz || error_exit "Failed to extract cmake"
cd cmake-3.21.1 || error_exit "Failed to enter cmake directory"
./bootstrap --prefix=$HOME/local || error_exit "Failed to bootstrap cmake"
make || error_exit "Failed to build cmake"
make install || error_exit "Failed to install cmake"
export PATH=$HOME/local/bin:$PATH || error_exit "Failed to update PATH for cmake"
cd ..


