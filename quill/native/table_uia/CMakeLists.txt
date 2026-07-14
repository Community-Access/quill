cmake_minimum_required(VERSION 3.20)
project(quill_table_uia CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# pybind11: pip install pybind11 (or vcpkg / conan).
find_package(pybind11 REQUIRED)

if(NOT WIN32)
    message(FATAL_ERROR "The Table Studio UIA provider is Windows-only.")
endif()

# UIAutomationCore.h / UIAutomation.h ship with the Windows 10 SDK (10.0.19041+).
pybind11_add_module(_quill_table_uia
    table_provider.cpp
    python_bridge.cpp
)

target_include_directories(_quill_table_uia PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(_quill_table_uia PRIVATE
    UIAutomationCore.lib
    oleaut32.lib
    uuid.lib
    user32.lib
)

if(MSVC)
    target_compile_options(_quill_table_uia PRIVATE
        /W4 /guard:cf /Qspectre /sdl
    )
    target_compile_definitions(_quill_table_uia PRIVATE
        _CRT_SECURE_NO_WARNINGS
        NOMINMAX
        UNICODE
        _UNICODE
    )
    set_property(TARGET _quill_table_uia PROPERTY
        MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

# Stage the built .pyd next to this CMakeLists so the build script can pick it
# up and copy it into the runtime; the Python side imports it optionally.
install(TARGETS _quill_table_uia
    LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}
    RUNTIME DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}
)

# Build (from this directory):
#   cmake -B build -G "Visual Studio 17 2022" -A x64
#   cmake --build build --config Release
#   cmake --install build --config Release
# Produces _quill_table_uia.pyd here; scripts/build_table_uia.py wraps this.
