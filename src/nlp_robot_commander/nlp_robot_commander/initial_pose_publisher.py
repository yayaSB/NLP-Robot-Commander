import math

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener


class InitialPosePublisher(Node):
    """Initialise AMCL avec la pose utilisée pour faire apparaître le robot."""

    def __init__(self) -> None:
        super().__init__("simulation_initial_pose")
        self.declare_parameter("x", -2.0)
        self.declare_parameter("y", -0.5)
        self.declare_parameter("yaw", 0.0)
        self.declare_parameter("frame_id", "map")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("scan_topic", "/scan")
        self.declare_parameter("publish_count", 5)
        self.declare_parameter("publish_interval_sec", 1.0)

        publish_count = int(self.get_parameter("publish_count").value)
        publish_interval = float(
            self.get_parameter("publish_interval_sec").value
        )
        if publish_count < 1:
            raise ValueError("publish_count doit être strictement positif.")
        if publish_interval <= 0:
            raise ValueError("publish_interval_sec doit être strictement positif.")

        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.publisher = self.create_publisher(
            PoseWithCovarianceStamped, "/initialpose", qos
        )
        self._scan_received = False
        self.scan_subscription = self.create_subscription(
            LaserScan,
            str(self.get_parameter("scan_topic").value),
            self._on_scan,
            qos_profile_sensor_data,
        )
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self._publish_count = publish_count
        self._published = 0
        self._timer = self.create_timer(publish_interval, self._try_publish)
        self.get_logger().info(
            "En attente d'AMCL et du premier scan lidar avant l'initialisation."
        )

    def _on_scan(self, _message: LaserScan) -> None:
        self._scan_received = True

    def _try_publish(self) -> None:
        map_frame = str(self.get_parameter("frame_id").value)
        base_frame = str(self.get_parameter("base_frame").value)
        if self._published > 0 and self.tf_buffer.can_transform(
            map_frame, base_frame, Time()
        ):
            self._timer.cancel()
            self.get_logger().info(
                "Localisation confirmée: la transformation map -> base_link est disponible."
            )
            return
        if self._published >= self._publish_count:
            return
        if not self._scan_received or self.publisher.get_subscription_count() == 0:
            return

        message = PoseWithCovarianceStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = map_frame
        message.pose.pose.position.x = float(self.get_parameter("x").value)
        message.pose.pose.position.y = float(self.get_parameter("y").value)
        yaw = float(self.get_parameter("yaw").value)
        message.pose.pose.orientation.z = math.sin(yaw / 2.0)
        message.pose.pose.orientation.w = math.cos(yaw / 2.0)

        # Incertitudes usuelles d'une estimation initiale RViz2 (x, y, yaw).
        message.pose.covariance[0] = 0.25
        message.pose.covariance[7] = 0.25
        message.pose.covariance[35] = (math.pi / 12.0) ** 2
        self.publisher.publish(message)
        self._published += 1
        self.get_logger().info(
            "Pose AMCL publiée "
            f"({self._published}/{self._publish_count}): "
            f"x={message.pose.pose.position.x:.2f}, "
            f"y={message.pose.pose.position.y:.2f}, yaw={yaw:.2f}"
        )
        if self._published == self._publish_count:
            self.get_logger().info(
                "Pose AMCL envoyée; attente de la transformation map -> base_link."
            )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = InitialPosePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
