from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def generate_launch_description() -> LaunchDescription:
    share = Path(get_package_share_directory("nlp_robot_commander"))
    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument("model_path", default_value=""),
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
                        "use_sim_time": ParameterValue(
                            LaunchConfiguration("use_sim_time"), value_type=bool
                        ),
                    },
                ],
            )
        ]
    )

