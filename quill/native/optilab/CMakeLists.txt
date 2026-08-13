# quill-optilab: QUILL's adapter executable around OptiLab Core.
#
# OptiLab Core is by Lanes Audio / dgl1984 -- https://github.com/dgl1984/optilab
# Vendored unmodified at v1.4.0 under upstream/, Apache-2.0 WITH Commons Clause
# v1.0 (see upstream/LICENSE and upstream/NOTICE).
#
# Only quill_optilab.cpp is QUILL's; it contains no DSP.
#
# Deliberately builds a plain executable rather than a Python extension:
# upstream states its C++ API is "not a stable C ABI", so QUILL drives it as a
# subprocess exactly like ffmpeg (see quill/core/optilab_adapter.py) instead of
# loading someone else's ABI into the interpreter.

cmake_minimum_required(VERSION 3.20)
project(quill_optilab CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if (MSVC)
    # Static CRT so the produced exe carries no redistributable dependency --
    # it ships next to the app and must run on a machine with no toolchain.
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

add_executable(quill-optilab
    quill_optilab.cpp
    upstream/OptiLabCore.cpp
)

target_include_directories(quill-optilab PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

if (MSVC)
    target_compile_options(quill-optilab PRIVATE /W4 /permissive- /O2)
else()
    target_compile_options(quill-optilab PRIVATE -Wall -Wextra -O2)
endif()
