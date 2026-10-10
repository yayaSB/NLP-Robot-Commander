import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TerminalClient(Node):
    def __init__(self) -> None:
        super().__init__("nlp_terminal_client")
        self.publisher = self.create_publisher(String, "/nlp_command", 10)
        self.worker = threading.Thread(target=self._read_commands, daemon=True)
        self.worker.start()

    def _read_commands(self) -> None:
        print("Saisissez une commande en français (`quit` pour sortir).")
        while rclpy.ok():
            try:
                text = input("> ").strip()
            except EOFError:
                text = "quit"
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

