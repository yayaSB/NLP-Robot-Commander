import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MicrophoneClient(Node):
    def __init__(self) -> None:
        super().__init__("nlp_microphone_client")
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise RuntimeError(
                "Installez les dépendances de requirements-audio.txt."
            ) from exc
        self.sr = sr
        self.recognizer = sr.Recognizer()
        self.publisher = self.create_publisher(String, "/nlp_command", 10)
        self.timer = self.create_timer(0.1, self._listen_once)
        self.busy = False
        self.get_logger().info("Entrée micro active; parlez après le message d'écoute.")

    def _listen_once(self) -> None:
        if self.busy:
            return
        self.busy = True
        try:
            with self.sr.Microphone() as source:
                self.get_logger().info("Écoute...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
            text = self.recognizer.recognize_google(audio, language="fr-FR")
            message = String()
            message.data = text
            self.publisher.publish(message)
            self.get_logger().info(f"Reconnu: {text}")
        except self.sr.WaitTimeoutError:
            pass
        except self.sr.UnknownValueError:
            self.get_logger().warning("Phrase non reconnue.")
        except self.sr.RequestError as exc:
            self.get_logger().error(f"Service de transcription indisponible: {exc}")
        finally:
            self.busy = False


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MicrophoneClient()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

