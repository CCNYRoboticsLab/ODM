FROM nvidia/cuda:12.2.0-devel-ubuntu20.04 AS builder

# Env variables
ENV DEBIAN_FRONTEND=noninteractive \
  PYTHONPATH="$PYTHONPATH:/code/SuperBuild/install/lib/python3.9/dist-packages:/code/SuperBuild/install/lib/python3.8/dist-packages:/code/SuperBuild/install/bin/opensfm" \
  LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/code/SuperBuild/install/lib"

# Prepare directories
WORKDIR /code

# Copy everything
COPY . ./

# Install necessary tools
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  gnupg

# Add Kitware GPG key
RUN curl -sSL https://apt.kitware.com/keys/kitware-archive-latest.asc | gpg --dearmor -o /usr/share/keyrings/kitware-archive-keyring.gpg

# Add Kitware repository
RUN echo "deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu focal main" >> /etc/apt/sources.list.d/kitware.list

# Update package lists
RUN apt-get update

# Run the build
RUN PORTABLE_INSTALL=YES GPU_INSTALL=YES bash configure.sh install

# Clean Superbuild
# RUN bash configure.sh clean

### END Builder

### Use a second image for the final asset to reduce the number and
# size of the layers.
FROM nvidia/cuda:12.2.0-runtime-ubuntu20.04
#FROM nvidia/cuda:11.2.0-devel-ubuntu20.04

# Env variables
ENV DEBIAN_FRONTEND=noninteractive \
  PYTHONPATH="$PYTHONPATH:/code/SuperBuild/install/lib/python3.9/dist-packages:/code/SuperBuild/install/lib/python3.8/dist-packages:/code/SuperBuild/install/bin/opensfm" \
  LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/code/SuperBuild/install/lib" \
  PDAL_DRIVER_PATH="/code/SuperBuild/install/bin"

WORKDIR /code

# Copy everything we built from the builder
COPY --from=builder /code /code

# Copy the Python libraries installed via pip from the builder
COPY --from=builder /usr/local /usr/local

# Install shared libraries that we depend on via APT, but *not*
# the -dev packages to save space!
# Also run a smoke test on ODM and OpenSfM
RUN bash configure.sh installruntimedepsonly \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
  && bash run.sh --help \
  && bash -c "eval $(python3 /code/opendm/context.py) && python3 -c 'from opensfm import io, pymap'"
# Entry point
# ENTRYPOINT ["python3", "/code/run.py"]
ENTRYPOINT [ "node", "/var/www/NodeODM/NodeODM/index.js" ]
