cmake_minimum_required(VERSION 3.8.3)
project(livox_laser_simulation)

## Compile as C++11, supported in ROS Kinetic and newer
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  tf
  sensor_msgs
  std_msgs

  livox_ros_driver
)

find_package(gazebo REQUIRED)
find_package(PCL REQUIRED)
include_directories(${GAZEBO_INCLUDE_DIRS})



#To solve the error which gazebo does not handle the include file well, we must add this line.
include_directories(/usr/include/)

link_directories(${GAZEBO_LIBRARY_DIRS})



include_directories(
         include
        ${catkin_INCLUDE_DIRS}
        ${PCL_INCLUDE_DIRS}
)

catkin_package(
        INCLUDE_DIRS include
        LIBRARIES livox_laser_simulation
        CATKIN_DEPENDS tf
)

add_library(livox_laser_simulation SHARED src/livox_points_plugin.cpp src/livox_ode_multiray_shape.cpp)
target_link_libraries(livox_laser_simulation ${catkin_LIBRARIES} RayPlugin)

target_link_libraries(livox_laser_simulation libprotobuf.so.9)
