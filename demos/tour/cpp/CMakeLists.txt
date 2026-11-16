# Builds the tour against the C++ that `temper build -b cpp` generates at the
# repo's top, with Argmas's own CMake project:
#
#     cmake -B build && cmake --build build --target tour && ./build/tour ARGS...

cmake_minimum_required(VERSION 3.16)
project(argmas_tour CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_subdirectory(../../../temper.out/cpp/argmas argmas)

add_executable(tour tour.cpp)
target_link_libraries(tour PRIVATE argmas)
