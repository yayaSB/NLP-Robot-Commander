import json
import math
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, Twist
from nav2_simple_commander.robot_navigator import BasicNavigator
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

from .command_processor import CommandProcessor
from .entity_extractor import EntityExtractor
from .intent_classifier import RuleBasedIntentClassifier, TransformersIntentClassifier


class NlpCommanderNode(Node):
    def __init__(self) -> None:
        super().__init__("nlp_commander")
        self._declare_parameters()

        waypoints_file = self.get_parameter("waypoints_file").value
        self.extractor = EntityExtractor.from_yaml(waypoints_file)
        classifier = self._build_classifier()
        self.processor = CommandProcessor(
            classifier,
            self.extractor,
            float(self.get_parameter("confidence_threshold").value),
        )

        self.navigator = BasicNavigator()
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.status_publisher = self.create_publisher(
            String, self.get_parameter("status_topic").value, 10
        )
        self.pick_publisher = self.create_publisher(
            String, self.get_parameter("pick_topic").value, 10
        )
        self.velocity_publisher = self.create_publisher(
            Twist, self.get_parameter("cmd_vel_topic").value, 10
        )
        self.command_subscription = self.create_subscription(
            String,
            self.get_parameter("input_topic").value,
            self._on_command,
            10,
        )
        self.navigation_active = False
        self.navigation_timer = self.create_timer(0.5, self._monitor_navigation)
        self.get_logger().info("NLP Robot Commander prêt à recevoir des commandes.")

    def _declare_parameters(self) -> None:
        default_config = (
            Path(get_package_share_directory("nlp_robot_commander"))
            / "config"
            / "waypoints.yaml"
        )
        self.declare_parameter("classifier_backend", "transformers")
        self.declare_parameter("model_path", "models/distilbert-robot-commander")
        self.declare_parameter("waypoints_file", str(default_config))
        self.declare_parameter("confidence_threshold", 0.65)
        self.declare_parameter("allow_rule_fallback", True)
        self.declare_parameter("input_topic", "/nlp_command")
        self.declare_parameter("status_topic", "/nlp_commander/status")
        self.declare_parameter("pick_topic", "/nlp_commander/pick_request")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("base_frame", "base_link")

    def _build_classifier(self):
        backend = str(self.get_parameter("classifier_backend").value).lower()
        if backend == "rules":
            self.get_logger().warning("Classifieur lexical actif (mode secours).")
            return RuleBasedIntentClassifier()
        if backend != "transformers":
            raise ValueError(f"Backend inconnu: {backend}")

        model_path = self.get_parameter("model_path").value
        try:
            classifier = TransformersIntentClassifier(model_path)
            self.get_logger().info(f"Checkpoint DistilBERT chargé: {model_path}")
            return classifier
        except Exception as exc:
            if not self.get_parameter("allow_rule_fallback").value:
                raise
            self.get_logger().warning(
                f"Checkpoint indisponible ({exc}); activation du mode lexical de secours."
            )
            return RuleBasedIntentClassifier()

    def _on_command(self, message: String) -> None:
        decision = self.processor.process(message.data)
        self._publish_status(
            "command_parsed",
            text=message.data,
            accepted=decision.accepted,
            intent=decision.intent,
            confidence=round(decision.confidence, 4),
            destination=decision.destination,
            object=decision.object_name,
            error_code=decision.error_code,
            message=decision.message,
        )
        if not decision.accepted:
            self.get_logger().warning(f"Commande refusée: {decision.message}")
            return

        if decision.intent == "navigate":
            self._navigate(decision.destination)
        elif decision.intent == "stop":
            self._stop()
        elif decision.intent == "pick":
            self._request_pick(decision.object_name, message.data)
        elif decision.intent == "report":
            self._report_position()

    def _navigate(self, destination: str) -> None:
        waypoint = self.extractor.waypoint(destination)
        goal = PoseStamped()
        goal.header.frame_id = self.get_parameter("map_frame").value
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.pose.position.x = float(waypoint["x"])
        goal.pose.position.y = float(waypoint["y"])
        yaw = float(waypoint.get("yaw", 0.0))
        goal.pose.orientation.z = math.sin(yaw / 2.0)
        goal.pose.orientation.w = math.cos(yaw / 2.0)
        self.navigator.goToPose(goal)
        self.navigation_active = True
        self._publish_status(
            "navigation_started",
            destination=destination,
            x=goal.pose.position.x,
            y=goal.pose.position.y,
            yaw=yaw,
        )

    def _stop(self) -> None:
        self.navigator.cancelTask()
        self.velocity_publisher.publish(Twist())
        self.navigation_active = False
        self._publish_status("navigation_cancelled", zero_velocity_sent=True)

    def _request_pick(self, object_name: str, original_text: str) -> None:
        request = String()
        request.data = json.dumps(
            {"object": object_name, "command": original_text}, ensure_ascii=False
        )
        self.pick_publisher.publish(request)
        self._publish_status(
            "pick_requested",
            object=object_name,
            note="Requête publiée; un manipulateur doit s'abonner au topic pick.",
        )

    def _report_position(self) -> None:
        map_frame = self.get_parameter("map_frame").value
        base_frame = self.get_parameter("base_frame").value
        try:
            transform = self.tf_buffer.lookup_transform(
                map_frame, base_frame, rclpy.time.Time()
            )
        except TransformException as exc:
            self._publish_status("position_failed", error=str(exc))
            return
        translation = transform.transform.translation
        rotation = transform.transform.rotation
        yaw = math.atan2(
            2.0 * (rotation.w * rotation.z + rotation.x * rotation.y),
            1.0 - 2.0 * (rotation.y**2 + rotation.z**2),
        )
        self._publish_status(
            "position_report",
            frame=map_frame,
            x=round(translation.x, 3),
            y=round(translation.y, 3),
            yaw=round(yaw, 3),
        )

    def _monitor_navigation(self) -> None:
        if not self.navigation_active or not self.navigator.isTaskComplete():
            return
        self.navigation_active = False
        result = self.navigator.getResult()
        self._publish_status("navigation_finished", result=str(result))

    def _publish_status(self, event: str, **payload) -> None:
        message = String()
        message.data = json.dumps({"event": event, **payload}, ensure_ascii=False)
        self.status_publisher.publish(message)
        self.get_logger().info(message.data)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NlpCommanderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.navigator.destroy_node()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
