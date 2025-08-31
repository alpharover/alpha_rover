cmake_minimum_required(VERSION 3.10)
project(alpha_lidar_airy_cpp)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(diagnostic_msgs REQUIRED)
find_package(yaml-cpp REQUIRED)

add_executable(reorder_node_cpp src/reorder_node.cpp)
ament_target_dependencies(reorder_node_cpp rclcpp sensor_msgs diagnostic_msgs)
target_link_libraries(reorder_node_cpp yaml-cpp)

install(TARGETS reorder_node_cpp
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
