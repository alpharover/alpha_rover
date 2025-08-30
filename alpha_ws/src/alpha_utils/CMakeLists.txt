cmake_minimum_required(VERSION 3.8)
project(alpha_utils)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)

set(MSG_FILES
  msg/Heartbeat.msg
  msg/DomainHealth.msg
  msg/Health.msg
  msg/ModeState.msg
  msg/Power.msg
  msg/Event.msg
  msg/LidarState.msg
  msg/DegradeBudget.msg
)

set(SRV_FILES
  srv/ModeSet.srv
  srv/GetConfig.srv
  srv/TriggerRecord.srv
  srv/OrchestratorCommand.srv
  srv/SetLidarMode.srv
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${MSG_FILES}
  ${SRV_FILES}
  DEPENDENCIES builtin_interfaces
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
