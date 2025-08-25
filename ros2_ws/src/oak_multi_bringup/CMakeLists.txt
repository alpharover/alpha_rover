cmake_minimum_required(VERSION 3.8)
project(oak_multi_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch config urdf
  DESTINATION share/${PROJECT_NAME}
)

# helpful but optional
install(FILES package.xml
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
