"""
MessageBroker: Sistema di comunicazione tra agenti basato su RabbitMQ.
Diviso in due classi separate per publishing e consuming.
"""
import json
import traceback
import uuid
import logging
from typing import Dict, Any, Callable, Optional, List, Tuple
import threading
import time
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosed, ChannelClosedByBroker, StreamLostError
import sys
from utils.logger import Logger


class MessagePublisher:
    """Classe dedicata alla pubblicazione di messaggi su RabbitMQ."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza il MessagePublisher con la configurazione specificata.
        
        Args:
            config: Configurazione per il MessagePublisher che include:
                - host: Host del server RabbitMQ
                - port: Porta del server RabbitMQ
                - username: Username per l'autenticazione
                - password: Password per l'autenticazione
                - virtual_host: Host virtuale (default: '/')
                - exchange: Nome dell'exchange (default: 'maia')
                - exchange_type: Tipo di exchange (default: 'topic')
                - connection_attempts: Numero di tentativi di connessione
                - retry_delay: Ritardo tra i tentativi di connessione (in secondi)
                - heartbeat: Intervallo di heartbeat in secondi
        """
        self._config = config
        self._connection = None
        self._channel = None
        self._exchange = config.get('exchange', 'maia')
        self._exchange_type = config.get('exchange_type', 'topic')
        self._stopping = False

    def connect(self) -> bool:
        """
        Stabilisce la connessione al message broker RabbitMQ.
        
        Returns:
            True se la connessione è stabilita con successo
        """
        try:
            # Parametri di connessione
            connection_params = pika.ConnectionParameters(
                host=self._config.get('host', 'localhost'),
                port=self._config.get('port', 5672),
                virtual_host=self._config.get('virtual_host', '/'),
                credentials=pika.PlainCredentials(
                    username=self._config.get('username', 'guest'),
                    password=self._config.get('password', 'guest')
                ),
                connection_attempts=self._config.get('connection_attempts', 3),
                retry_delay=self._config.get('retry_delay', 2),
                heartbeat=self._config.get('heartbeat', 60)
            )
            
            # Stabilisce la connessione
            self._connection = pika.BlockingConnection(connection_params)
            self._channel = self._connection.channel()
            
            # Dichiara l'exchange
            self._channel.exchange_declare(
                exchange=self._exchange,
                exchange_type=self._exchange_type,
                durable=True
            )
            
            print(f"Publisher connected to RabbitMQ at {self._config.get('host', 'localhost')}:{self._config.get('port', 5672)}")
            return True
        
        except AMQPConnectionError as e:
            print(f"Failed to connect to RabbitMQ: {e}")
            return False
        
        except Exception as e:
            print(f"Unexpected error connecting to RabbitMQ: {e}")
            return False

    def disconnect(self) -> None:
        """
        Chiude la connessione al message broker.
        """
        self._stopping = True
        print("Disconnecting Publisher from RabbitMQ")
        
        # Chiude il canale
        if self._channel and self._channel.is_open:
            try:
                self._channel.close()
            except Exception as e:
                print(f"Error closing publisher channel: {e}")
            finally:
                self._channel = None
        
        # Chiude la connessione
        if self._connection and self._connection.is_open:
            try:
                self._connection.close()
            except Exception as e:
                print(f"Error closing publisher connection: {e}")
            finally:
                self._connection = None

    def _ensure_connection(self) -> bool:
        """
        Assicura che ci sia una connessione attiva a RabbitMQ.
        Se necessario, tenta di riconnettersi.
        
        Returns:
            True se la connessione è attiva
        """
        if self._stopping:
            return False
            
        if self._connection and self._connection.is_open and self._channel and self._channel.is_open:
            return True
        
        try:
            print("Ensuring publisher connection to RabbitMQ by reconnecting")
            self.disconnect()
            return self.connect()
        except Exception as e:
            print(f"Error ensuring publisher connection: {e}")
            return False

    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Pubblica un messaggio su un topic specifico.
        
        Args:
            topic: Topic su cui pubblicare
            message: Messaggio da pubblicare
            
        Returns:
            True se la pubblicazione ha avuto successo
        """
        if not self._ensure_connection():
            print("Publisher: Failed to ensure connection")
            return False
        
        try:
            # Prepara il corpo del messaggio
            message_body = json.dumps(message)
            print(f"Publishing message to {topic}: {message_body}")
            
            # Pubblica il messaggio
            self._channel.basic_publish(
                exchange=self._exchange,
                routing_key=topic,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Rende il messaggio persistente
                    content_type='application/json'
                )
            )
            
            return True
            
        except AMQPChannelError as e:
            print(f"Channel error publishing to {topic}: {e}")
            return False
            
        except Exception as e:
            print(f"Error publishing to {topic}: {e}")
            traceback.print_exc()
            return False


class MessageConsumer:
    """Classe dedicata al consumo di messaggi da RabbitMQ."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza il MessageConsumer con la configurazione specificata.
        
        Args:
            config: Configurazione per il MessageConsumer (stessi parametri del Publisher)
        """
        self._config = config
        self._connection = None
        self._channel = None
        self._exchange = config.get('exchange', 'maia')
        self._exchange_type = config.get('exchange_type', 'topic')
        self._subscribers = {}  # {subscription_id: (topic, callback, queue_name)}
        self._consuming = False
        self._consumer_thread = None
        self._should_reconnect = False
        self._stopping = False
        self._declared_queues = set()

    def connect(self) -> bool:
        """
        Stabilisce la connessione al message broker RabbitMQ.
        
        Returns:
            True se la connessione è stabilita con successo
        """
        try:
            # Parametri di connessione
            connection_params = pika.ConnectionParameters(
                host=self._config.get('host', 'localhost'),
                port=self._config.get('port', 5672),
                virtual_host=self._config.get('virtual_host', '/'),
                credentials=pika.PlainCredentials(
                    username=self._config.get('username', 'guest'),
                    password=self._config.get('password', 'guest')
                ),
                connection_attempts=self._config.get('connection_attempts', 3),
                retry_delay=self._config.get('retry_delay', 2),
                heartbeat=self._config.get('heartbeat', 60)
            )
            
            # Stabilisce la connessione
            self._connection = pika.BlockingConnection(connection_params)
            self._channel = self._connection.channel()
            
            # Dichiara l'exchange
            self._channel.exchange_declare(
                exchange=self._exchange,
                exchange_type=self._exchange_type,
                durable=True
            )
            
            print(f"Consumer connected to RabbitMQ at {self._config.get('host', 'localhost')}:{self._config.get('port', 5672)}")
            return True
        
        except AMQPConnectionError as e:
            print(f"Failed to connect consumer to RabbitMQ: {e}")
            return False
        
        except Exception as e:
            print(f"Unexpected error connecting consumer to RabbitMQ: {e}")
            return False

    def disconnect(self) -> None:
        """
        Chiude la connessione al message broker.
        """
        print("Disconnecting Consumer from RabbitMQ")
        self._stopping = True
        
        # Ferma il consumo di messaggi
        if self._channel:
            try:
                if self._channel.is_open:
                    self._channel.stop_consuming()
            except (ConnectionClosed, ChannelClosedByBroker, StreamLostError, IndexError) as e:
                print(f"Gracefully handled stop_consuming error: {e.__class__.__name__} - {e}")
            except Exception as e:
                print(f"Unexpected error stopping consumption: {e}")
        
        # Attende che il thread del consumer si fermi
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join(timeout=5)
        
        # Chiude il canale
        if self._channel and self._channel.is_open:
            try:
                self._channel.close()
            except Exception as e:
                print(f"Error closing consumer channel: {e}")
            finally:
                self._channel = None
        
        # Chiude la connessione
        if self._connection and self._connection.is_open:
            try:
                self._connection.close()
            except Exception as e:
                print(f"Error closing consumer connection: {e}")
            finally:
                self._connection = None

    def _ensure_connection(self) -> bool:
        """
        Assicura che ci sia una connessione attiva a RabbitMQ.
        Se necessario, tenta di riconnettersi.
        
        Returns:
            True se la connessione è attiva
        """
        if self._stopping:
            return False
            
        if self._connection and self._connection.is_open and self._channel and self._channel.is_open:
            return True
        
        try:
            print("Ensuring consumer connection to RabbitMQ by reconnecting")
            self.disconnect()
            return self.connect()
        except Exception as e:
            print(f"Error ensuring consumer connection: {e}")
            return False

    def _declare_queue(self, queue_name: str, topic: str) -> bool:
        """
        Dichiara una coda e la lega all'exchange.
        
        Args:
            queue_name: Nome della coda da dichiarare
            topic: Topic a cui legare la coda
            
        Returns:
            True se la dichiarazione ha avuto successo
        """
        if not self._ensure_connection():
            return False
            
        try:
            # Dichiara la coda
            queue_result = self._channel.queue_declare(
                queue=queue_name,
                durable=True,
                auto_delete=False
            )
            actual_queue_name = queue_result.method.queue
            
            print(f"Consumer queue name: {actual_queue_name} topic: {topic}")
            
            # Lega la coda all'exchange con il routing key (topic)
            self._channel.queue_bind(
                exchange=self._exchange,
                queue=actual_queue_name,
                routing_key=topic
            )
            
            self._declared_queues.add(actual_queue_name)
            return True
            
        except Exception as e:
            print(f"Error declaring queue {queue_name} for topic {topic}: {e}")
            return False

    def _message_handler_wrapper(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Wrapper per gestire i messaggi ricevuti.
        
        Args:
            callback: Funzione callback originale
            
        Returns:
            Funzione wrapper per pika
        """
        def wrapper(ch, method, properties, body):
            try:
                # Decodifica il messaggio JSON
                message = json.loads(body.decode('utf-8'))
                print(f"Received message: {message}")
                
                # Chiama la callback dell'utente
                callback(message)
                
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON message: {e}")
            except Exception as e:
                print(f"Error in message callback: {e}")
                traceback.print_exc()
        
        return wrapper

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> str:
        """
        Sottoscrive a un topic specifico.
        
        Args:
            topic: Topic a cui sottoscriversi (supporta wildcards * e #)
            callback: Funzione da chiamare quando arriva un messaggio
            
        Returns:
            ID di sottoscrizione
        """
        if not self._ensure_connection():
            raise ConnectionError("Consumer not connected to RabbitMQ")
        
        # Genera un ID di sottoscrizione univoco
        subscription_id = str(uuid.uuid4())
        
        # Crea un nome di coda univoco per questa sottoscrizione
        queue_name = f"maia.{topic.replace('.', '_').replace('*', 'star').replace('#', 'hash')}.{subscription_id[:8]}"
        print(f"Consumer queue name: {queue_name}")
        
        # Dichiara la coda e la lega al topic
        if not self._declare_queue(queue_name, topic):
            raise RuntimeError(f"Failed to declare queue for topic {topic}")
                
        # Imposta il consumatore per la coda
        try:
            print("Consumer ready to consume")
            wrapped_callback = self._message_handler_wrapper(callback)
            
            self._channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=True
            )
            
            # Avvia il consumo se non è già attivo
            if not self._consuming:
                self._start_consuming()
                
        except Exception as e:
            print(f"Error setting up consumer for queue {queue_name}: {e}")
            raise RuntimeError(f"Failed to set up consumer for topic {topic}")
        
        # Memorizza la sottoscrizione
        self._subscribers[subscription_id] = (topic, callback, queue_name)
        
        print(f"Subscribed to {topic} with ID {subscription_id}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Annulla una sottoscrizione.
        
        Args:
            subscription_id: ID della sottoscrizione da annullare
            
        Returns:
            True se l'annullamento ha avuto successo
        """
        if subscription_id not in self._subscribers:
            print(f"Subscription {subscription_id} not found")
            return False
        
        if not self._ensure_connection():
            print("Consumer not connected to RabbitMQ")
            return False
        
        try:
            # Recupera le informazioni sulla sottoscrizione
            _, _, queue_name = self._subscribers[subscription_id]
            
            # Annulla il consumatore
            self._channel.basic_cancel(consumer_tag=queue_name)
            
            # Elimina la coda
            self._channel.queue_delete(queue=queue_name)
            
            # Rimuove la sottoscrizione dalla lista
            del self._subscribers[subscription_id]
            
            print(f"Unsubscribed from {subscription_id}")
            return True
            
        except Exception as e:
            print(f"Error unsubscribing from {subscription_id}: {e}")
            return False

    def _start_consuming(self) -> None:
        """
        Avvia il consumo di messaggi in un thread separato.
        """
        if self._consumer_thread and self._consumer_thread.is_alive():
            return
            
        def consumer_thread():
            while not self._stopping:
                if self._ensure_connection():
                    try:
                        self._consuming = True
                        print("Consumer starting to consume messages")
                        self._channel.start_consuming()
                    except AMQPConnectionError:
                        print("Consumer: AMQP Connection error, retrying in 5 seconds")
                        time.sleep(5)
                    except Exception as e:
                        print(f"Consumer: Error in consuming thread: {e}")
                        traceback.print_exc()
                        time.sleep(1)
                    finally:
                        self._consuming = False
                else:
                    print("Consumer: Failed to ensure connection, retrying in 5 seconds")
                    time.sleep(5)
                    
        self._consumer_thread = threading.Thread(target=consumer_thread, daemon=True)
        self._consumer_thread.start()

    def create_queue(self, queue_name: str) -> bool:
        """
        Crea una nuova coda.
        
        Args:
            queue_name: Nome della coda da creare
            
        Returns:
            True se la creazione ha avuto successo
        """
        if not self._ensure_connection():
            return False
        
        try:
            # Dichiara la coda
            self._channel.queue_declare(
                queue=queue_name,
                durable=True,
                auto_delete=False
            )
            
            self._declared_queues.add(queue_name)
            print(f"Created queue {queue_name}")
            return True
            
        except Exception as e:
            print(f"Error creating queue {queue_name}: {e}")
            return False


# Esempio di utilizzo
if __name__ == "__main__":
    # Configurazione RabbitMQ
    config = {
        'host': 'localhost',
        'port': 5672,
        'username': 'admin',
        'password': 'password',
        'exchange': 'maia'
    }
    
    # Crea publisher e consumer separati
    publisher = MessagePublisher(config)
    consumer = MessageConsumer(config)
    
    # Connetti entrambi
    if publisher.connect() and consumer.connect():
        print("Both publisher and consumer connected successfully")
        
        # Esempio di callback per i messaggi ricevuti
        def message_callback(ch, method, properties, body):
            print(f"Received: {body.decode('utf-8')}")
        
        # Sottoscrivi a un topic
        subscription_id = consumer.subscribe("test.topic", message_callback)
        
        # Pubblica un messaggio
        publisher.publish("test.topic", {"message": "Hello World!"})
        
        # Mantieni il programma in esecuzione per un po'
        time.sleep(5)
        
        # Cleanup
        consumer.unsubscribe(subscription_id)
        consumer.disconnect()
        publisher.disconnect()
    else:
        print("Failed to connect to RabbitMQ")