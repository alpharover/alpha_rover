cmake_minimum_required(VERSION 3.8)
project(alpha_mapping)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(nvblox src/nvblox_dummy_node.cpp)
ament_target_dependencies(nvblox rclcpp sensor_msgs)

add_executable(mapping_node src/mapping_node.cpp)
ament_target_dependencies(mapping_node rclcpp sensor_msgs)

install(TARGETS nvblox
  DESTINATION lib/${PROJECT_NAME}
)

install(TARGETS mapping_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

ament_package()
