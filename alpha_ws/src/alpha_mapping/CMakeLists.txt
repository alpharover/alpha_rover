cmake_minimum_required(VERSION 3.8)
project(alpha_mapping)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(alpha_utils REQUIRED)
find_package(pluginlib REQUIRED)

add_executable(nvblox src/nvblox_dummy_node.cpp)
ament_target_dependencies(nvblox rclcpp sensor_msgs)

add_executable(mapping_node src/mapping_node.cpp)
ament_target_dependencies(mapping_node rclcpp sensor_msgs alpha_utils)

install(TARGETS nvblox
  DESTINATION lib/${PROJECT_NAME}
)

install(TARGETS mapping_node
  DESTINATION lib/${PROJECT_NAME}
)

add_library(nvblox_provider SHARED src/nvblox_provider.cpp)
ament_target_dependencies(nvblox_provider rclcpp sensor_msgs pluginlib)

pluginlib_export_plugin_description_file(alpha_mapping plugin_description.xml)

install(TARGETS nvblox_provider
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(FILES plugin_description.xml
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

ament_package()
