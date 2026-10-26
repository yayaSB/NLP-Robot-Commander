import sys
import threading

try:
    import readline
except ImportError:  # pragma: no cover - ROS 2 Humble s'exécute sous Linux/WSL.
    readline = None

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TerminalClient(Node):
    def __init__(self) -> None:
        super().__init__("nlp_terminal_client")
        self.publisher = self.create_publisher(String, "/nlp_command", 10)
        self.status_subscription = self.create_subscription(
            String, "/nlp_commander/status", self._on_status, 10
        )
        self.input_active = threading.Event()
        self.worker = threading.Thread(target=self._read_commands, daemon=True)
        self.worker.start()

    def _on_status(self, message: String) -> None:
        """Affiche un statut ROS sans masquer l'invite de commande."""
        prompt_was_active = self.input_active.is_set()
        if prompt_was_active:
            sys.stdout.write("\r\033[2K")
        sys.stdout.write(f"{message.data}\n")
        sys.stdout.flush()
        if prompt_was_active:
            if readline is not None:
                readline.redisplay()
            else:
                sys.stdout.write("> ")
                sys.stdout.flush()

    def _read_commands(self) -> None:
        print("Saisissez une commande en français (`quit` pour sortir).")
        while rclpy.ok():
            try:
                self.input_active.set()
                text = input("> ").strip()
            except EOFError:
                text = "quit"
            finally:
                self.input_active.clear()
            if text.casefold() in {"quit", "exit", "q"}:
                rclpy.shutdown()
                return
            if text:
                message = String()
                message.data = text
                self.publisher.publish(message)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TerminalClient()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, RuntimeError):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

