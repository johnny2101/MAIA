import threading
import json
from typing import Dict, List, Any, Tuple
from integrations.gemma import Google_Gemini_Integration
from data.prompts.dispatcher_prompts import DispatcherPrompts
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

        def user_message_callback(**kwargs):
                try:
                    ch, method, properties, body = kwargs['ch'], kwargs['method'], kwargs['properties'], kwargs['body']
                except KeyError as e:
                    print(f"Error unpacking message: {e}")
                    return
                if self._stop_event.is_set():
                    ch.stop_consuming()
                    return
                
                payload: Dict[str, Any] = body
                chat_id = payload.get("chat_id")
                response_text = payload.get("text", "no message found")
                response = self.analyze_request(response_text)
                
                selected_agents = self.route_request(response)
                
                self._message_publisher.publish("dispatcher.log.info", f"Selected agents: {selected_agents}")
                self._message_publisher.publish(f"agent.{selected_agents}.request", response)

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
        response = json.loads(response)
        self._message_publisher.publish("dispatcher.log.info", response)
        return response

    def detect_intent(self, message: Dict[str, Any]) -> str:
        pass

    def route_request(self, message: Dict[str, Any]) -> List[str]:
        """
        Inoltra la richiesta agli agenti appropriati in base all'intento e alle entità rilevate.
        
        Args:
            message (Dict[str, Any]): Il messaggio da inoltrare.
        
        Returns:
            List[str]: Lista degli agenti selezionati per gestire la richiesta.
        """
        primary_intent = self.detect_intent(message)
        selected_agents = message.get("selected_agent", [])
        
        if not selected_agents:
            fallback_agent = self.fallback_strategy(message)
            selected_agents.append(fallback_agent)
        
        return selected_agents

    def dispatch(self, message: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        pass

    def fallback_strategy(self, message: Dict[str, Any]) -> str:
        pass
