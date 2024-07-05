set(_SB_BINARY_DIR "${SB_BINARY_DIR}/pypopsift")
set(YOUR_GPU_COMPUTE_CAPABILITY 86)

# Pypopsift
find_package(CUDA)

if (CUDA_VERSION VERSION_LESS 7.0)
    message(FATAL_ERROR "CUDA version ${CUDA_VERSION} is too old.  Requires CUDA 7.0 or later.")
endif()

# if(CUDA_FOUND)
#     ExternalProject_Add(pypopsift
#         DEPENDS           opensfm
#         PREFIX            ${_SB_BINARY_DIR}
#         TMP_DIR           ${_SB_BINARY_DIR}/tmp
#         STAMP_DIR         ${_SB_BINARY_DIR}/stamp
#         #--Download step--------------
#         DOWNLOAD_DIR      ${SB_DOWNLOAD_DIR}
#         GIT_REPOSITORY    https://github.com/OpenDroneMap/pypopsift
#         GIT_TAG           288
#         #--Update/Patch step----------
#         UPDATE_COMMAND    ""
#         #--Configure step-------------
#         SOURCE_DIR        ${SB_SOURCE_DIR}/pypopsift
#         CMAKE_ARGS
#             -DCUDA_NVCC_FLAGS="-gencode arch=compute_${YOUR_GPU_COMPUTE_CAPABILITY}, code=sm_${YOUR_GPU_COMPUTE_CAPABILITY}" # Add this line
#             -DOUTPUT_DIR=${SB_INSTALL_DIR}/bin/opensfm/opensfm
#             -DCMAKE_INSTALL_PREFIX=${SB_INSTALL_DIR}
#             ${WIN32_CMAKE_ARGS}
#             ${ARM64_CMAKE_ARGS}
#         #--Build step-----------------
#         BINARY_DIR        ${_SB_BINARY_DIR}
#         #--Install step---------------
#         INSTALL_DIR       ${SB_INSTALL_DIR}
#         #--Output logging-------------
#         LOG_DOWNLOAD      OFF
#         LOG_CONFIGURE     OFF
#         LOG_BUILD         OFF
#         )
# else()
#     message(WARNING "Could not find CUDA >= 7.0")
# endif()