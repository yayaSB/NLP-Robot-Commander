from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    share = Path(get_package_share_directory("nlp_robot_commander"))
    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument("model_path", default_value=""),
            DeclareLaunchArgument("llm_enabled", default_value="false"),
            DeclareLaunchArgument("llm_model", default_value="llama3.2:1b"),
            Node(
                package="nlp_robot_commander",
                executable="nlp_commander",
                name="nlp_commander",
                output="screen",
                parameters=[
                    str(share / "config" / "commander.yaml"),
                    {
                        "waypoints_file": str(share / "config" / "waypoints.yaml"),
                        "model_path": LaunchConfiguration("model_path"),
                        "llm_enabled": ParameterValue(
                            LaunchConfiguration("llm_enabled"), value_type=bool
                        ),
                        "llm_model": LaunchConfiguration("llm_model"),
                        "use_sim_time": ParameterValue(
                            LaunchConfiguration("use_sim_time"), value_type=bool
                        ),
                    },
                ],
            )
        ]
    )

