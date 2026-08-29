# QuillVille native launcher -- one Win32 executable per product.
#
# This CMake project compiles the same launcher.c + runtime_resolve.c into
# one executable per product (radio, weather, audio studio, main quill, ...).
# The product identity is supplied via -DPRODUCT_* at the build script
# level; here we expose a single target per product, and the Python
# build wrapper invokes this project once per product.
#
# On Windows the executable links against shell32, shlwapi, and user32
# (for the GetModuleFileNameA / PathRemoveFileSpecA / MessageBoxA calls).
# On macOS / Linux the POSIX path is used (no link-time deps beyond libc).
#
# This mirrors the toolchain conventions in quill/native/table_uia/CMakeLists.txt.

cmake_minimum_required(VERSION 3.20)
project(quill_launcher C)

if(NOT WIN32 AND NOT APPLE AND NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR
        "The QuillVille launcher builds for Windows, macOS, and Linux. "
        "Found unsupported platform: ${CMAKE_SYSTEM_NAME}.")
endif()

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
# We use _WIN32_WINNT etc. below; C extensions must be on (default for
# MSVC anyway, but be explicit so clang / gcc on the per-platform
# runners don't disable them).
set(CMAKE_C_EXTENSIONS ON)

if(MSVC)
    add_compile_options(/W4 /guard:cf /Qspectre)
    add_compile_definitions(
        _CRT_SECURE_NO_WARNINGS
        NOMINMAX
        UNICODE
        _UNICODE
        WIN32_LEAN_AND_MEAN
    )
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

# Per-product build: the Python wrapper invokes this with -DPRODUCT_NAME=...
# and -DPRODUCT_DISPLAY_NAME=... etc. We make a single executable target
# named after the product.
#
# The Python wrapper does the per-product invocation:
#
#   cmake -B build/<product> -G "Visual Studio 17 2022" -A x64 \
#         -DPRODUCT_NAME=quill-radio \
#         -DPRODUCT_DISPLAY_NAME="Quill Radio" \
#         -DPRODUCT_VERSION=2.2.0 \
#         -DPRODUCT_PYTHON_MODULE=quill.apps.radio \
#         -DPRODUCT_REPO=Community-Access/quill \
#         -DPRODUCT_APP_ID=CommunityAccess.QuillRadio
#
# Then cmake --build build/<product> --config Release produces
# build/<product>/Release/quill-radio.exe (or the platform equivalent).

if(NOT DEFINED PRODUCT_NAME)
    message(FATAL_ERROR
        "PRODUCT_NAME is required (e.g. -DPRODUCT_NAME=quill-radio). "
        "This CMakeLists is meant to be invoked once per product by "
        "scripts/build_native_launcher.py.")
endif()

# The self-healing launcher downloads the QuillVille Runtime installer from this
# URL when no runtime is found. Overridable per product; the default points at
# the dedicated moving `runtime-latest` release tag. NOT releases/latest: that
# path follows the repository's newest non-prerelease release, which is owned
# by the editor's release train and carries no runtime asset -- the runtime
# ships on its own cadence under its own tag.
if(NOT DEFINED PRODUCT_RUNTIME_URL)
    set(PRODUCT_RUNTIME_URL
        "https://github.com/Community-Access/quill/releases/download/runtime-latest/QuillVille-Runtime-Setup.exe")
endif()

# Generate product.h from product.h.in, with the values supplied at configure
# time. This is the only template-style file in the project.
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/product.h.in
    ${CMAKE_CURRENT_BINARY_DIR}/product.h
    @ONLY
)

# Generate the Windows resource file. version.rc.in embeds the per-product
# VERSIONINFO (ProductName, FileDescription, OriginalFilename, ...) and,
# when -DPRODUCT_ICON is set, the user-facing icon group. The resource is
# compiled only on Windows; macOS / Linux launchers get their identity
# from the executable filename and (later) a Mac bundle plist.
#
# The COMMA-separated version (used by FILEVERSION / PRODUCTVERSION which
# expect WORD WORD WORD WORD) is a derived value -- we split the dotted
# string here rather than asking the caller to pass it twice.
if(WIN32)
    string(REPLACE "." "," PRODUCT_VERSION_COMMA "${PRODUCT_VERSION}")
    set(PRODUCT_ICON_PATH "")
    if(DEFINED PRODUCT_ICON AND EXISTS "${PRODUCT_ICON}")
        # Convert the path the user passed to a Windows backslash form
        # for the .rc file. The .rc compiler is a Windows tool, so
        # forward slashes work in practice, but backslashes are
        # what RC expects in resource-string fields.
        file(TO_NATIVE_PATH "${PRODUCT_ICON}" PRODUCT_ICON_PATH)
    endif()
    configure_file(
        ${CMAKE_CURRENT_SOURCE_DIR}/version.rc.in
        ${CMAKE_CURRENT_BINARY_DIR}/version.rc
        @ONLY
    )
endif()

add_executable(${PRODUCT_NAME}
    launcher.c
    runtime_resolve.c
    runtime_bootstrap.c
)

if(WIN32)
    target_sources(${PRODUCT_NAME} PRIVATE
        ${CMAKE_CURRENT_BINARY_DIR}/version.rc
    )
endif()

target_include_directories(${PRODUCT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}
)

if(WIN32)
    target_link_libraries(${PRODUCT_NAME} PRIVATE
        shell32
        shlwapi
        user32
        urlmon
        comctl32
        ole32
    )
    set_target_properties(${PRODUCT_NAME} PROPERTIES
        WIN32_EXECUTABLE TRUE
        OUTPUT_NAME "${PRODUCT_NAME}"
    )
endif()

if(APPLE)
    set_target_properties(${PRODUCT_NAME} PROPERTIES
        MACOSX_BUNDLE FALSE
        OUTPUT_NAME "${PRODUCT_NAME}"
    )
endif()

# Install the built executable into the source tree so the Python wrapper
# can pick it up without having to know the per-config subdirectory layout
# (Release/ on MSVC, the root on Unix makefiles).
install(TARGETS ${PRODUCT_NAME}
    RUNTIME DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}
)
