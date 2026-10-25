import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


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
            DeclareLaunchArgument("params_file", default_value=default_params),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("auto_initial_pose", default_value="true"),
            DeclareLaunchArgument("initial_x", default_value="-2.0"),
            DeclareLaunchArgument("initial_y", default_value="-0.5"),
            DeclareLaunchArgument("initial_yaw", default_value="0.0"),
            DeclareLaunchArgument("model_path", default_value=""),
            DeclareLaunchArgument("llm_enabled", default_value="false"),
            DeclareLaunchArgument("llm_model", default_value="llama3.2:1b"),
            DeclareLaunchArgument("llm_timeout_sec", default_value="60.0"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(turtlebot_gazebo, "launch", "turtlebot3_world.launch.py")
                ),
                launch_arguments={
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                    "x_pose": LaunchConfiguration("initial_x"),
                    "y_pose": LaunchConfiguration("initial_y"),
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(turtlebot_navigation, "launch", "navigation2.launch.py")
                ),
                launch_arguments={
                    "map": LaunchConfiguration("map"),
                    "params_file": LaunchConfiguration("params_file"),
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                }.items(),
            ),
            TimerAction(
                period=3.0,
                actions=[
                    Node(
                        package="nlp_robot_commander",
                        executable="initial_pose_publisher",
                        name="simulation_initial_pose",
                        output="screen",
                        condition=IfCondition(
                            LaunchConfiguration("auto_initial_pose")
                        ),
                        parameters=[
                            {
                                "x": ParameterValue(
                                    LaunchConfiguration("initial_x"), value_type=float
                                ),
                                "y": ParameterValue(
                                    LaunchConfiguration("initial_y"), value_type=float
                                ),
                                "yaw": ParameterValue(
                                    LaunchConfiguration("initial_yaw"), value_type=float
                                ),
                                "use_sim_time": ParameterValue(
                                    LaunchConfiguration("use_sim_time"), value_type=bool
                                ),
                            }
                        ],
                    )
                ],
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
