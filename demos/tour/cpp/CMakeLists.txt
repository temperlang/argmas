# Builds the tour against the C++ that `temper build -b cpp` generates at the
# repo's top, with Argmas's own CMake project:
#
#     cmake -B build && cmake --build build --target tour && ./build/tour ARGS...
#
# and the site's section examples, the same way, as `examples`.

cmake_minimum_required(VERSION 3.16)
project(argmas_tour CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_subdirectory(../../../temper.out/cpp/argmas argmas)

add_executable(tour tour.cpp)
target_link_libraries(tour PRIVATE argmas)

add_executable(examples examples.cpp)
target_link_libraries(examples PRIVATE argmas)
