import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    turtlebot_gazebo = get_package_share_directory("turtlebot3_gazebo")
    turtlebot_navigation = get_package_share_directory("turtlebot3_navigation2")
    commander = get_package_share_directory("nlp_robot_commander")
    default_map = os.path.join(turtlebot_navigation, "map", "map.yaml")
    default_params = os.path.join(
        turtlebot_navigation, "param", "humble", "burger.yaml"
    )

    return LaunchDescription(
        [
            SetEnvironmentVariable("TURTLEBOT3_MODEL", "burger"),
            DeclareLaunchArgument("map", default_value=default_map),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("model_path", default_value=""),
            DeclareLaunchArgument("llm_enabled", default_value="false"),
            DeclareLaunchArgument("llm_model", default_value="llama3.2:1b"),
            DeclareLaunchArgument("llm_timeout_sec", default_value="60.0"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(turtlebot_gazebo, "launch", "turtlebot3_world.launch.py")
                )
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(turtlebot_navigation, "launch", "navigation2.launch.py")
                ),
                launch_arguments={
                    "map": LaunchConfiguration("map"),
                    "params_file": default_params,
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(commander, "launch", "nlp_commander.launch.py")
                ),
                launch_arguments={
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                    "model_path": LaunchConfiguration("model_path"),
                    "llm_enabled": LaunchConfiguration("llm_enabled"),
                    "llm_model": LaunchConfiguration("llm_model"),
                    "llm_timeout_sec": LaunchConfiguration("llm_timeout_sec"),
                }.items(),
            ),
        ]
    )
