import threading
import json
from typing import Dict, List, Any, Tuple
from integrations.gemma import Google_Gemini_Integration
from data.prompts.dispatcher_prompts import DispatcherPrompts
from core.message_broker2 import MessageBroker
from core.message_broker import MessageConsumer, MessagePublisher

class Dispatcher:
    """
    Analizza le richieste degli utenti e le indirizza agli agenti appropriati.
    """
    
    def __init__(self, agent_manager=None, config: Dict[str, Any] = {}):
        """
        Inizializza il Dispatcher.
        """
        self._agent_manager = agent_manager
        self._config = config
        self._gemini = Google_Gemini_Integration()
        self._prompts = DispatcherPrompts().get_prompt("system_prompt")
        message_broker_config = {
            'host': 'localhost',
            'port': 5672,
            'username': 'admin',
            'password': 'password',
            'virtual_host': '/'
        }
        self._message_publisher = MessagePublisher(message_broker_config)
        self._message_consumer = MessageConsumer(message_broker_config)
        if not self._message_consumer.connect() or not self._message_publisher.connect():
            print("Failed to connect to RabbitMQ")
            exit(1)

        self._stop_event = threading.Event()
        self._listener_thread = None

    def _listen_to_user_messages(self):
        """
        Sottoscrive ai messaggi utente e gestisce i messaggi ricevuti.
        """
        topic = "user.message.new"

        def user_message_callback(ch, method, properties, body):
            if self._stop_event.is_set():
                ch.stop_consuming()
                return
            
            payload = json.loads(body.decode())
            payload = json.loads(payload)
            chat_id = payload.get("chat_id")
            response_text = payload.get("text", "no message found")
            response = self.analyze_request(response_text)
            
            payload = {
                "chat_id": chat_id,
                "text": response,
            }
            
            self._message_publisher.publish("user.message.processed", json.dumps(payload))

        try:
            self._message_consumer.subscribe(topic, user_message_callback)
        except Exception as e:
            self._message_publisher.publish("dispatcher.log.error", f"Error while listening to messages: {e}")

    def stop_listening(self):
        """
        Ferma l'ascolto dei messaggi utente.
        """
        self._stop_event.set()
        self._message_publisher.disconnect()
        self._message_consumer.disconnect()
        if self._listener_thread:
            self._listener_thread.join()
            print("Dispatcher listening thread stopped.")

    def analyze_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        response = self._gemini.send_message_with_system_instruction(self._prompts, message)
        self._message_publisher.publish("dispatcher.log.info", response)
        return response

    def detect_intent(self, message: Dict[str, Any]) -> str:
        pass

    def route_request(self, message: Dict[str, Any]) -> List[str]:
        pass

    def dispatch(self, message: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        pass

    def fallback_strategy(self, message: Dict[str, Any]) -> str:
        pass
