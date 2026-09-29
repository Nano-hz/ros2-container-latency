# Official ROS 2 Humble base image is Ubuntu 22.04 (Jammy).
FROM ros:humble-ros-base

# Nodes are bind-mounted at runtime, so the image needs no project-specific
# build layer or additional apt packages.
WORKDIR /ros_nodes

