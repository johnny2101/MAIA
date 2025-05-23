"""
MessageBroker: Sistema di comunicazione tra agenti basato su RabbitMQ.
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

class MessageBroker:

    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza il MessageBroker con la configurazione specificata.
        
        Args:
            config: Configurazione per il MessageBroker che include:
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
        self._connection = None  # Connessione a RabbitMQ
        self._channel = None  # Canale di comunicazione
        self._exchange = config.get('exchange', 'maia')
        self._exchange_type = config.get('exchange_type', 'topic')
        self._subscribers = {}  # Callback registrati per topic: {subscription_id: (topic, callback, queue_name)}
        self._consuming = False  # Flag per indicare se si sta consumando messaggi
        self._consumer_thread = None  # Thread per consumare messaggi in background
        self._should_reconnect = False  # Flag per indicare se è necessario riconnettersi
        self._reconnect_delay = 0  # Ritardo per la riconnessione
        self._stopping = False  # Flag per indicare se il broker è in fase di arresto
        self._declared_queues = set()  # Set delle code già dichiarate

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
            
            #logger.info(f"Connected to RabbitMQ at {self._config.get('host', 'localhost')}:{self._config.get('port', 5672)}")
            return True
        
        except AMQPConnectionError as e:
            #logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
        
        except Exception as e:
            #logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
            return False

    def disconnect(self) -> None:
        print("Disconnecting from RabbitMQ")
        """
        Chiude la connessione al message broker.
        """
        self._stopping = True
        
        # Ferma il consumo di messaggi
        '''if self._consuming:
            try:
                if self._channel.is_open:
                    print("stopping consuming")
                    self._channel.stop_consuming()
                self._consuming = False
            except Exception as e:
                print(f"Error stopping consumption: {e}")
                traceback.print_exc()'''
        if self._channel:
            try:
                if self._channel.is_open:
                    self._channel.stop_consuming()
            except (ConnectionClosed, ChannelClosedByBroker, StreamLostError, IndexError) as e:
                print(f"Gracefully handled stop_consuming error: {e.__class__.__name__} - {e}")
            except Exception as e:
                print(f"Unexpected error stopping consumption: {e}")
        
        # Chiude il canale
        if self._channel.is_open:
            print("closing channel")
            try:
                self._channel.close()
            except Exception as e:
                print(f"Error closing channel: {e}")
                traceback.print_exc()
            finally:
                self._channel = None
        
        # Chiude la connessione
        if self._connection and self._connection.is_open:
            try:
                self._connection.close()
            except Exception as e:
                print(f"Error closing connection: {e}")
            finally:
                self._connection = None
        
        #logger.info("Disconnected from RabbitMQ")

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
            print("Connection is already open")
            return True
        
        try:
            print("Ensuring connection to RabbitMQ by disconnecting and reconnecting")
            self.disconnect()  # Chiude eventuali connessioni esistenti
            return self.connect()
        except Exception as e:
            #logger.error(f"Error ensuring connection: {e}")
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
        if not self._connection or self._connection.is_closed:
            print("Connection is closed. Reconnecting...")
            self.connect()

        # Ricontrolla canale
        if not self._channel or self._channel.is_closed:
            print("Channel is closed. Reopening channel...")
            self._channel = self._connection.channel()
            self._channel.exchange_declare(exchange=self._exchange_name, exchange_type='topic', durable=True)
        
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
            
            
            #logger.debug(f"Published message to {topic}: {message_body[:100]}...")
            return True
            
        except AMQPChannelError as e:
            #logger.error(f"Channel error publishing to {topic}: {e}")
            print(f"Channel error publishing to {topic}: {e}")
            return False
            
        except Exception as e:
            #logger.error(f"Error publishing to {topic}: {e}")
            print(f"Error publishing to {topic}: {e}")
            traceback.print_exc()
            return False

    def _message_callback(self, ch, method, properties, body, callback: Callable):
        """
        Callback interno invocato quando arriva un messaggio.
        
        Args:
            ch: Canale
            method: Metodo di consegna
            properties: Proprietà del messaggio
            body: Corpo del messaggio
            callback: Callback dell'utente da invocare
        """
        try:
            # Decodifica il messaggio
            message = json.loads(body)
            
            # Invoca il callback dell'utente
            callback(message)
            
            # Conferma la ricezione del messaggio
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except json.JSONDecodeError:
            #logger.error(f"Failed to decode message: {body}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            #logger.error(f"Error processing message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

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
            queue_name_actual = self._channel.queue_declare(
                queue=queue_name,
                durable=True,
                auto_delete=False
            )
            queue_name_actual = queue_name_actual.method.queue
            
            print(f"queue name: {queue_name} topic: {topic}")
            
            # Lega la coda all'exchange con il routing key (topic)
            self._channel.queue_bind(
                exchange=self._exchange,
                queue=queue_name,
                routing_key=topic
            )
            
            self._declared_queues.add(queue_name)
            return True
            
        except Exception as e:
            #logger.error(f"Error declaring queue {queue_name} for topic {topic}: {e}")
            return False

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
            raise ConnectionError("Not connected to RabbitMQ")
        
        # Genera un ID di sottoscrizione univoco
        subscription_id = str(uuid.uuid4())
        
        # Crea un nome di coda univoco per questa sottoscrizione
        queue_name = f"maia.{topic.replace('.', '_').replace('*', 'star').replace('#', 'hash')}.{subscription_id[:8]}"
        print(f"queue name: {queue_name}")
        
        # Dichiara la coda e la lega al topic
        if not self._declare_queue(queue_name, topic):
            raise RuntimeError(f"Failed to declare queue for topic {topic}")
                
        # Imposta il consumatore per la coda
        try:
            print("ready to consume")
            self._channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=True
            )
            try:
                if not self._consuming:
                    self._start_consuming()
            except Exception as e:
                print(f"[MessageBroker] Consuming stopped: {e}")
                traceback.print_exc()
        except Exception as e:
            #logger.error(f"Error setting up consumer for queue {queue_name}: {e}")
            raise RuntimeError(f"Failed to set up consumer for topic {topic}")

        
        # Memorizza la sottoscrizione
        self._subscribers[subscription_id] = (topic, callback, queue_name)
        
        #logger.info(f"Subscribed to {topic} with ID {subscription_id}")
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
            #logger.warning(f"Subscription {subscription_id} not found")
            return False
        
        if not self._ensure_connection():
            #logger.error("Not connected to RabbitMQ")
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
            
            #logger.info(f"Unsubscribed from {subscription_id}")
            return True
            
        except Exception as e:
            #logger.error(f"Error unsubscribing from {subscription_id}: {e}")
            return False

    def _start_consuming(self) -> None:
        if self._consumer_thread and self._consumer_thread.is_alive():
            return

        def consumer_thread():
            while not self._stopping:
                if self._ensure_connection():
                    try:
                        self._consuming = True
                        print("starting consumingg")
                        self._channel.start_consuming()
                    except AMQPConnectionError:
                        time.sleep(5)
                    except Exception as e:
                        traceback.print_exc()
                        time.sleep(1)
                    finally:
                        self._consuming = False
                else:
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
            #logger.info(f"Created queue {queue_name}")
            return True
            
        except Exception as e:
            #logger.error(f"Error creating queue {queue_name}: {e}")
            return False

    def enqueue(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """
        Inserisce un messaggio in una coda.
        
        Args:
            queue_name: Nome della coda
            message: Messaggio da inserire
            
        Returns:
            True se l'inserimento ha avuto successo
        """
        if not self._ensure_connection():
            return False
        
        # Crea la coda se non esiste
        if queue_name not in self._declared_queues:
            if not self.create_queue(queue_name):
                return False
        
        try:
            # Prepara il corpo del messaggio
            message_body = json.dumps(message)
            
            # Pubblica il messaggio direttamente nella coda (senza exchange)
            self._channel.basic_publish(
                exchange='',  # Default exchange
                routing_key=queue_name,  # Il routing key è il nome della coda
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Rende il messaggio persistente
                    content_type='application/json'
                )
            )
            
            #logger.debug(f"Enqueued message to {queue_name}: {message_body[:100]}...")
            return True
            
        except Exception as e:
            #logger.error(f"Error enqueuing message to {queue_name}: {e}")
            return False

    def dequeue(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Preleva un messaggio da una coda.
        
        Args:
            queue_name: Nome della coda
            
        Returns:
            Messaggio prelevato o None se la coda è vuota
        """
        if not self._ensure_connection():
            return None
        
        try:
            # Preleva un messaggio dalla coda
            method_frame, header_frame, body = self._channel.basic_get(
                queue=queue_name,
                auto_ack=True  # Conferma automaticamente la ricezione
            )
            
            if method_frame:
                # Decodifica il messaggio
                message = json.loads(body)
                #logger.debug(f"Dequeued message from {queue_name}")
                return message
            else:
                #logger.debug(f"No message available in queue {queue_name}")
                return None
                
        except Exception as e:
            #logger.error(f"Error dequeuing message from {queue_name}: {e}")
            return None

    def list_queues(self) -> List[str]:
        """
        Elenca le code dichiarate.
        
        Returns:
            Lista dei nomi delle code
        """
        if not self._ensure_connection():
            return []
        
        try:
            # Ottiene informazioni sulle code
            queues_info = self._channel.queue_declare(queue='', exclusive=True)
            queue_name = queues_info.method.queue
            
            # Ottiene le code legate all'exchange
            bindings = self._channel.queue_bind(
                exchange=self._exchange,
                queue=queue_name,
                routing_key='#'
            )
            
            # Estrae i nomi delle code
            queue_names = [binding.queue for binding in bindings]
            return queue_names
            
        except Exception as e:
            #logger.error(f"Error listing queues: {e}")
            return []

if __name__ == "__main__":
    # Configurazione di test
    config = {
        'host': 'localhost',
        'port': 5672,
        'username': 'admin',
        'password': 'password',
        'virtual_host': '/'
    }
    
    broker = MessageBroker(config)
    
    if not broker.connect():
        #logger.error("Failed to connect to RabbitMQ")
        exit(1)
    queue_name = "test.queue"
    
    if len(sys.argv) > 1:
        def callback2(ch, method, properies, body):
            print(f" [x] {method.routing_key}:{body}")

        subscription_id = broker.subscribe("user.message.new", callback2)
        
        while True:
            time.sleep(2)    
    else:
    # Pubblicazione di un messaggio
        test_message = "What's the weather like in Rome today?"
        broker.publish("user.message.processed", test_message)
        
        broker.enqueue(queue_name, {"action": "test", "data": "queue test"})
    
    
    
    
    # Pulizia
    
    broker.disconnect()
    