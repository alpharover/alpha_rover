cmake_minimum_required(VERSION 3.5)
project(oak_nvblox_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

# Install Python scripts (utilities)
install(PROGRAMS
  scripts/pointcloud_merge.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
