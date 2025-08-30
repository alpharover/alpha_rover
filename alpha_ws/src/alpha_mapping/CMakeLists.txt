cmake_minimum_required(VERSION 3.8)
project(alpha_mapping)

find_package(ament_cmake REQUIRED)

install(DIRECTORY include/
  DESTINATION include
)

ament_package()

