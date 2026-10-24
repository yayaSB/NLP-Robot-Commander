import json
import math
import queue
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import rclpy
from action_msgs.msg import GoalStatus
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

from .command_memory import CommandMemory
from .command_processor import CommandProcessor
from .command_router import CommandRouter
from .entity_extractor import EntityExtractor
from .intent_classifier import (
    ModelLoadError,
    RuleBasedIntentClassifier,
    TransformersIntentClassifier,
)
from .llm_interpreter import OllamaLlmInterpreter
from .navigation_state import NavigationPhase, NavigationStateMachine, StopState


class NlpCommanderNode(Node):
    """Adaptateur ROS 2 entre une commande validée et Nav2/TF."""

    def __init__(self) -> None:
        super().__init__("nlp_commander")
        self._declare_parameters()
        self._validate_parameters()

        self.extractor = EntityExtractor.from_yaml(
            self.get_parameter("waypoints_file").value
        )
        self.memory = self._build_memory()
        llm_interpreter = self._build_llm_interpreter()
        self.processor = CommandProcessor(
            self._build_classifier(),
            self.extractor,
            float(self.get_parameter("confidence_threshold").value),
            float(self.get_parameter("ambiguity_margin").value),
            int(self.get_parameter("max_command_chars").value),
            llm_interpreter=llm_interpreter,
            memory=self.memory,
            llm_history_size=int(self.get_parameter("llm_history_size").value),
            allow_llm_fallback=bool(
                self.get_parameter("llm_fallback_to_classifier").value
            ),
        )
        self.router = CommandRouter(self)
        self.navigation = NavigationStateMachine()
        self.goal_handle = None
        self.cancel_deadline_ns: int | None = None
        self._command_epoch = 0
        self._nlp_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="nlp-llm"
        )
        self._nlp_results: queue.SimpleQueue = queue.SimpleQueue()
        self._pending_nlp: Future | None = None

        self.action_client = ActionClient(
            self,
            NavigateToPose,
            self.get_parameter("navigate_action").value,
        )
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.status_publisher = self.create_publisher(
            String, self.get_parameter("status_topic").value, 10
        )
        self.velocity_publisher = None
        if self.get_parameter("publish_zero_velocity_on_stop").value:
            self.velocity_publisher = self.create_publisher(
                Twist, self.get_parameter("cmd_vel_topic").value, 10
            )
        self.command_subscription = self.create_subscription(
            String,
            self.get_parameter("input_topic").value,
            self._on_command,
            10,
        )
        self.watchdog_timer = self.create_timer(0.1, self._check_cancel_timeout)
        self.nlp_result_timer = self.create_timer(0.05, self._drain_nlp_results)
        self.get_logger().info("NLP Robot Commander prêt à recevoir des commandes.")

    def _declare_parameters(self) -> None:
        default_config = (
            Path(get_package_share_directory("nlp_robot_commander"))
            / "config"
            / "waypoints.yaml"
        )
        self.declare_parameter("classifier_backend", "transformers")
        self.declare_parameter("model_path", "")
        self.declare_parameter("waypoints_file", str(default_config))
        self.declare_parameter("confidence_threshold", 0.65)
        self.declare_parameter("ambiguity_margin", 0.10)
        self.declare_parameter("max_command_chars", 240)
        self.declare_parameter("allow_rule_fallback", False)
        self.declare_parameter("llm_enabled", False)
        self.declare_parameter("llm_model", "llama3.2:1b")
        self.declare_parameter("llm_endpoint", "http://127.0.0.1:11434")
        self.declare_parameter("llm_timeout_sec", 20.0)
        self.declare_parameter("llm_history_size", 8)
        self.declare_parameter("llm_memory_max_entries", 200)
        self.declare_parameter("llm_memory_db_path", "")
        self.declare_parameter("llm_fallback_to_classifier", True)
        self.declare_parameter("input_topic", "/nlp_command")
        self.declare_parameter("status_topic", "/nlp_commander/status")
        self.declare_parameter("navigate_action", "/navigate_to_pose")
        self.declare_parameter("nav_server_timeout_sec", 3.0)
        self.declare_parameter("cancel_timeout_sec", 3.0)
        self.declare_parameter("tf_timeout_sec", 0.5)
        self.declare_parameter("max_tf_age_sec", 1.0)
        self.declare_parameter("publish_zero_velocity_on_stop", False)
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("base_frame", "base_link")

    def _validate_parameters(self) -> None:
        for name in (
            "nav_server_timeout_sec",
            "cancel_timeout_sec",
            "tf_timeout_sec",
            "max_tf_age_sec",
            "llm_timeout_sec",
        ):
            if float(self.get_parameter(name).value) <= 0:
                raise ValueError(f"{name} doit être strictement positif.")
        for name in ("llm_history_size", "llm_memory_max_entries"):
            if int(self.get_parameter(name).value) < 1:
                raise ValueError(f"{name} doit être strictement positif.")

    def _build_memory(self) -> CommandMemory | None:
        if not self.get_parameter("llm_enabled").value:
            return None
        configured = str(self.get_parameter("llm_memory_db_path").value).strip()
        if configured:
            path = Path(configured).expanduser()
            if not path.is_absolute():
                raise ValueError("llm_memory_db_path doit être un chemin absolu.")
        else:
            path = (
                Path.home()
                / ".local"
                / "share"
                / "nlp_robot_commander"
                / "command_memory.sqlite3"
            )
        memory = CommandMemory(
            path, int(self.get_parameter("llm_memory_max_entries").value)
        )
        self.get_logger().info(f"Mémoire locale des commandes: {path}")
        return memory

    def _build_llm_interpreter(self) -> OllamaLlmInterpreter | None:
        if not self.get_parameter("llm_enabled").value:
            self.get_logger().info("LLM local désactivé; DistilBERT reste actif.")
            return None
        interpreter = OllamaLlmInterpreter(
            tuple(self.extractor.waypoints),
            model=str(self.get_parameter("llm_model").value),
            endpoint=str(self.get_parameter("llm_endpoint").value),
            timeout_sec=float(self.get_parameter("llm_timeout_sec").value),
        )
        self.get_logger().info(
            "LLM local activé via Ollama: "
            f"{self.get_parameter('llm_model').value}"
        )
        return interpreter

    def _build_classifier(self):
        backend = str(self.get_parameter("classifier_backend").value).casefold()
        if backend == "rules":
            self.get_logger().warning("Classifieur lexical explicitement activé.")
            return RuleBasedIntentClassifier()
        if backend != "transformers":
            raise ValueError(f"Backend inconnu: {backend}")

        model_path = str(self.get_parameter("model_path").value).strip()
        if not model_path:
            raise ValueError("model_path absolu requis pour le backend transformers.")
        resolved_model_path = Path(model_path).expanduser()
        if not resolved_model_path.is_absolute():
            raise ValueError("model_path doit être un chemin absolu.")
        try:
            classifier = TransformersIntentClassifier(resolved_model_path)
        except ModelLoadError as exc:
            if not self.get_parameter("allow_rule_fallback").value:
                raise
            self.get_logger().error(
                f"Checkpoint indisponible ({exc}); mode lexical explicitement autorisé."
            )
            return RuleBasedIntentClassifier()
        self.get_logger().info(f"Checkpoint DistilBERT chargé: {resolved_model_path}")
        return classifier

    def _on_command(self, message: String) -> None:
        text = message.data
        if self.processor.is_priority_stop(text):
            self._command_epoch += 1
            if self._pending_nlp is not None:
                self._pending_nlp.cancel()
            try:
                decision = self.processor.process(text)
            except Exception as exc:
                self._publish_status("command_error", error=str(exc))
                self.get_logger().error(f"Échec du traitement de l'arrêt: {exc}")
                return
            self._handle_decision(text, decision)
            return

        if self._pending_nlp is not None and not self._pending_nlp.done():
            self._publish_status("command_rejected", text=text, reason="nlp_busy")
            return
        epoch = self._command_epoch
        future = self._nlp_executor.submit(self.processor.process, text)
        self._pending_nlp = future

        def enqueue_result(completed: Future) -> None:
            self._nlp_results.put((epoch, text, completed))

        future.add_done_callback(
            enqueue_result
        )
        self._publish_status("command_processing", text=text)

    def _drain_nlp_results(self) -> None:
        while True:
            try:
                epoch, text, future = self._nlp_results.get_nowait()
            except queue.Empty:
                return
            if future is self._pending_nlp:
                self._pending_nlp = None
            if epoch != self._command_epoch:
                self._publish_status(
                    "command_discarded", text=text, reason="stop_received_after_command"
                )
                continue
            self._complete_nlp_future(text, future)

    def _complete_nlp_future(self, text: str, future: Future) -> None:
        try:
            decision = future.result()
        except Exception as exc:
            self._publish_status("command_error", error=str(exc))
            self.get_logger().error(f"Échec du traitement de la commande: {exc}")
            return
        self._handle_decision(text, decision)

    def _handle_decision(self, text: str, decision) -> None:
        self._publish_status(
            "command_parsed",
            text=text,
            accepted=decision.accepted,
            intent=decision.intent,
            confidence=round(decision.confidence, 4),
            destination=decision.destination,
            error_code=decision.error_code,
            message=decision.message,
            source=decision.source,
            memory_used=decision.memory_used,
        )
        try:
            routed = self.router.route(decision)
        except Exception as exc:
            self._publish_status("execution_error", error=str(exc))
            self.get_logger().error(f"Échec du routage de la commande: {exc}")
            return
        if not routed:
            self.get_logger().warning(f"Commande refusée: {decision.message}")
            return
        self.processor.remember(text, decision)
        if decision.source == "classifier_fallback":
            self.get_logger().warning(decision.message)

    def close(self) -> None:
        self._nlp_executor.shutdown(wait=True, cancel_futures=True)
        if self.memory is not None:
            self.memory.close()

    def navigate(self, destination: str) -> None:
        if self.navigation.phase != NavigationPhase.IDLE:
            self._publish_status(
                "navigation_rejected",
                reason="navigation_busy",
                phase=self.navigation.phase.value,
            )
            return
        timeout = float(self.get_parameter("nav_server_timeout_sec").value)
        try:
            server_available = self.action_client.wait_for_server(timeout_sec=timeout)
        except Exception as exc:
            self._publish_status(
                "navigation_rejected", reason="action_server_error", error=str(exc)
            )
            return
        if not server_available:
            self._publish_status("navigation_rejected", reason="action_server_unavailable")
            return

        waypoint = self.extractor.waypoint(destination)
        pose = PoseStamped()
        pose.header.frame_id = self.get_parameter("map_frame").value
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(waypoint["x"])
        pose.pose.position.y = float(waypoint["y"])
        yaw = float(waypoint["yaw"])
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)

        goal = NavigateToPose.Goal()
        goal.pose = pose
        self.navigation.request_goal(destination)
        try:
            future = self.action_client.send_goal_async(goal)
        except Exception as exc:
            self.navigation.reset()
            self._publish_status(
                "navigation_rejected", reason="goal_send_error", error=str(exc)
            )
            return
        future.add_done_callback(self._goal_response_callback)
        self._publish_status(
            "navigation_requested",
            destination=destination,
            frame=pose.header.frame_id,
            x=pose.pose.position.x,
            y=pose.pose.position.y,
            yaw=yaw,
        )

    def _goal_response_callback(self, future) -> None:
        stop_was_requested = self.navigation.stop_requested
        try:
            goal_handle = future.result()
            accepted = bool(goal_handle and goal_handle.accepted)
            cancel_immediately = self.navigation.goal_response(accepted)
        except Exception as exc:
            self.navigation.reset()
            self._publish_status("navigation_rejected", reason="goal_error", error=str(exc))
            if stop_was_requested:
                self._publish_status("stop_unconfirmed", reason="goal_response_error")
            return
        if not accepted:
            self._publish_status("navigation_rejected", reason="goal_rejected_by_nav2")
            return

        self.goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._navigation_result_callback)
        self._publish_status(
            "navigation_started", destination=self.navigation.destination
        )
        if cancel_immediately:
            self._send_cancel_request()

    def stop(self) -> None:
        self._publish_status("stop_received", phase=self.navigation.phase.value)
        outcome = self.navigation.request_stop()
        if self.velocity_publisher is not None:
            self.velocity_publisher.publish(Twist())
            self._publish_status(
                "zero_velocity_sent",
                note="Mesure complémentaire; ne confirme pas l'annulation Nav2.",
            )
        if outcome.state == StopState.CONFIRMED:
            self._publish_status("stop_confirmed", reason=outcome.reason)
        elif outcome.reason == "goal_response_pending":
            timeout = float(self.get_parameter("cancel_timeout_sec").value)
            self.cancel_deadline_ns = self.get_clock().now().nanoseconds + int(
                timeout * 1e9
            )
            self._publish_status("cancellation_pending", reason=outcome.reason)
        else:
            self._send_cancel_request()

    def _send_cancel_request(self) -> None:
        if self.goal_handle is None:
            self._publish_status("cancellation_pending", reason="goal_handle_pending")
            return
        timeout = float(self.get_parameter("cancel_timeout_sec").value)
        self.cancel_deadline_ns = self.get_clock().now().nanoseconds + int(timeout * 1e9)
        future = self.goal_handle.cancel_goal_async()
        future.add_done_callback(self._cancel_response_callback)
        self._publish_status("cancellation_requested", timeout_sec=timeout)

    def _cancel_response_callback(self, future) -> None:
        try:
            response = future.result()
            accepted = bool(response and response.goals_canceling)
            outcome = self.navigation.cancellation_response(accepted)
        except Exception as exc:
            self.cancel_deadline_ns = None
            if self.navigation.phase == NavigationPhase.CANCEL_PENDING:
                self.navigation.cancellation_response(False)
            self._publish_status("stop_unconfirmed", reason="cancel_error", error=str(exc))
            return
        if not accepted:
            self.cancel_deadline_ns = None
            self._publish_status("stop_unconfirmed", reason=outcome.reason)
            return
        self._publish_status("cancellation_accepted", reason=outcome.reason)

    def _check_cancel_timeout(self) -> None:
        if self.cancel_deadline_ns is None:
            return
        if self.get_clock().now().nanoseconds <= self.cancel_deadline_ns:
            return
        self.cancel_deadline_ns = None
        if (
            self.navigation.phase == NavigationPhase.GOAL_PENDING
            and self.navigation.stop_requested
        ):
            self._publish_status("stop_unconfirmed", reason="goal_response_timeout")
            return
        if self.navigation.phase == NavigationPhase.CANCEL_PENDING:
            outcome = self.navigation.cancellation_timeout()
            self._publish_status("stop_unconfirmed", reason=outcome.reason)

    def _navigation_result_callback(self, future) -> None:
        self.cancel_deadline_ns = None
        try:
            wrapped = future.result()
            status = wrapped.status
        except Exception as exc:
            outcome = self.navigation.complete("result_error")
            self.goal_handle = None
            self._publish_status("navigation_failed", reason="result_error", error=str(exc))
            if outcome:
                self._publish_status("stop_unconfirmed", reason=outcome.reason)
            return

        result_name = {
            GoalStatus.STATUS_SUCCEEDED: "succeeded",
            GoalStatus.STATUS_CANCELED: "canceled",
            GoalStatus.STATUS_ABORTED: "aborted",
        }.get(status, f"status_{status}")
        destination = self.navigation.destination
        outcome = self.navigation.complete(result_name)
        self.goal_handle = None
        event = "navigation_succeeded" if result_name == "succeeded" else "navigation_finished"
        self._publish_status(event, result=result_name, destination=destination)
        if outcome:
            stop_event = (
                "stop_confirmed"
                if outcome.state == StopState.CONFIRMED
                else "stop_unconfirmed"
            )
            self._publish_status(stop_event, reason=outcome.reason)

    def report(self) -> None:
        map_frame = self.get_parameter("map_frame").value
        base_frame = self.get_parameter("base_frame").value
        timeout = Duration(seconds=float(self.get_parameter("tf_timeout_sec").value))
        try:
            transform = self.tf_buffer.lookup_transform(
                map_frame, base_frame, Time(), timeout=timeout
            )
        except TransformException as exc:
            self._publish_status(
                "position_unavailable",
                map_frame=map_frame,
                base_frame=base_frame,
                navigation_phase=self.navigation.phase.value,
                error=str(exc),
            )
            return

        stamp_ns = Time.from_msg(transform.header.stamp).nanoseconds
        age_sec = (self.get_clock().now().nanoseconds - stamp_ns) / 1e9
        max_age = float(self.get_parameter("max_tf_age_sec").value)
        if stamp_ns <= 0 or age_sec < 0 or age_sec > max_age:
            self._publish_status(
                "position_stale",
                age_sec=round(age_sec, 3),
                max_age_sec=max_age,
                navigation_phase=self.navigation.phase.value,
            )
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
            age_sec=round(age_sec, 3),
            navigation_phase=self.navigation.phase.value,
        )

    def _publish_status(self, event: str, **payload) -> None:
        message = String()
        message.data = json.dumps({"event": event, **payload}, ensure_ascii=False)
        self.status_publisher.publish(message)
        self.get_logger().info(message.data)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = NlpCommanderNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.close()
            node.action_client.destroy()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
