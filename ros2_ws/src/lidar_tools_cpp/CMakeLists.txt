cmake_minimum_required(VERSION 3.5)
project(lidar_tools_cpp)

if(CMAKE_CXX_STANDARD STREQUAL "")
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(pc_reorder src/pc_reorder.cpp)
ament_target_dependencies(pc_reorder rclcpp sensor_msgs)

install(TARGETS pc_reorder DESTINATION lib/${PROJECT_NAME})

ament_package()

