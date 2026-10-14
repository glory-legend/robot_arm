cmake_minimum_required(VERSION 3.16)
project(robotiq_hande_description)

find_package(ament_cmake REQUIRED)

# 벤더링하면서 launch/rviz/cad_models 는 가져오지 않았다(NOTICE 참조).
install(
  DIRECTORY urdf meshes
  DESTINATION share/${PROJECT_NAME}
)

install(
  FILES LICENSE NOTICE
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
