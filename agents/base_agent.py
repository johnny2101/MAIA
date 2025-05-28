"""
Base Agent per MAIA (Modular Artificial Intelligence Assistant)

Classe base astratta che definisce l'interfaccia comune per tutti gli agenti specializzati.
Fornisce funzionalità condivise come gestione del contesto, logging, e comunicazione
con il message broker.
"""

from abc import ABC, abstractmethod
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import asyncio
from dataclasses import dataclass, field

from models.message import Message
from models.task import Task
from core.message_broker import MessageConsumer, MessagePublisher
from core.memory_manager import MemoryManager
from integrations.gemma import Google_Gemini_Integration


@dataclass
class AgentCapability:
    """Definisce una capacità specifica dell'agente"""
    name: str
    description: str
    keywords: List[str]
    confidence_threshold: float = 0.7
    requires_external_api: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Struttura di risposta standardizzata per tutti gli agenti"""
    success: bool
    content: str
    confidence: float
    agent_name: str
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    requires_followup: bool = False
    followup_suggestions: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class BaseAgent(ABC):
    """
    Classe base astratta per tutti gli agenti MAIA.
    
    Fornisce:
    - Gestione del contesto e memoria
    - Comunicazione con il message broker
    - Sistema di logging standardizzato
    - Gestione degli errori
    - Interfaccia comune per il processamento delle richieste
    """
    
    def __init__(
        self,
        agent_name: str,
        capabilities: List[AgentCapability],
        memory_manager: MemoryManager,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Inizializza l'agente base.
        
        Args:
            agent_name: Nome univoco dell'agente
            capabilities: Lista delle capacità dell'agente
            message_broker: Istanza del message broker per la comunicazione
            memory_manager: Istanza del memory manager per la persistenza
            config: Configurazioni specifiche dell'agente
        """
        self.agent_name = agent_name
        self.capabilities = capabilities
        config = {
            'host': 'localhost',
            'port': 5672,
            'username': 'admin',
            'password': 'password',
            'virtual_host': '/'
        }
        self.message_publisher = MessagePublisher(config)
        self.message_consumer = MessageConsumer(config)
        self.memory_manager = memory_manager
        self.config = config or {}
        self.google_gemini = Google_Gemini_Integration()
        
        # Configurazioni base
        self.is_active = False
        self.processing_timeout = self.config.get('processing_timeout', 30.0)
        self.max_context_length = self.config.get('max_context_length', 4000)
        
        # Metriche di performance
        self.total_requests = 0
        self.successful_requests = 0
        self.average_processing_time = 0.0
        
        # Registrazione automatica nel message broker
        self._register_with_broker()
        

    def _register_with_broker(self):
        """Registra l'agente nel message broker per ricevere messaggi"""
        try:
            # Registra l'agente per ricevere messaggi diretti
            self.message_consumer.subscribe(
                f"agent.{self.agent_name}.request",
                self._handle_broker_message
            )
            
            # Registra l'agente per messaggi broadcast se supportato
            if hasattr(self, 'supports_broadcast') and self.supports_broadcast:
                self.message_consumer.subscribe(
                    "broadcast.all_agents",
                    self._handle_broadcast_message
                )
                
        except Exception as e:
            self.message_publisher.publish(f"{self.agent_name}.logger.error",f"Errore nella registrazione con message broker: {e}")

    def _handle_broker_message(self, **kwargs):
        """Gestisce i messaggi ricevuti dal message broker"""
        
        try:
            
            method, properties, body = kwargs['method'], kwargs['properties'], kwargs['body']
            
            # Converte il messaggio in formato standard
            message = body.decode('utf-8')
            while type(message) is not dict:
                message = json.loads(message)
    
            # Processa il messaggio
            response = self.process_request(message)
            
            # Invia la risposta se richiesta
            '''if message.get('requires_response', False):
                self.message_publisher.publish(
                    f"agent.{self.agent_name}.response",
                    response.to_dict() if hasattr(response, 'to_dict') else response.__dict__
                )'''
                
        except Exception as e:
            self.message_publisher._ensure_connection()
            self.message_publisher.publish(
                f"{self.agent_name}.logger.error",
                f"Errore nella gestione del messaggio: {e}"
            )

    async def _handle_broadcast_message(self, message: Dict[str, Any]):
        """Gestisce i messaggi broadcast (da implementare negli agenti che lo supportano)"""
        pass

    def can_handle_request(self, message: Message) -> float:
        """
        Determina se l'agente può gestire una richiesta e con quale confidenza.
        
        Args:
            message: Messaggio da valutare
            
        Returns:
            Float tra 0.0 e 1.0 indicante la confidenza nella capacità di gestire la richiesta
        """
        max_confidence = 0.0
        
        for capability in self.capabilities:
            confidence = self._calculate_capability_confidence(message, capability)
            max_confidence = max(max_confidence, confidence)
            
        return max_confidence
    
    def qwery_llm(self, system_prompt:str, message: str) -> AgentResponse:
        """
        Interroga il modello LLM per ottenere una risposta.
        
        Args:
            system_prompt: Istruzione di sistema per il modello LLM
            message: Messaggio da processare
            
        Returns:
            AgentResponse con il risultato del processamento
        """
        try:
            response = self.google_gemini.send_message_with_system_instruction(system_prompt, message)
            
            #save response data to file
            with open("response_data.json", "w") as file:
                json.dump(response, file, indent=4)
            return response
        except Exception as e:
            print(f"Errore nell'interrogazione del modello LLM: {e}")
            self.message_publisher.publish(
                f"{self.agent_name}.logger.error",
                f"Errore nell'interrogazione del modello LLM: {e}"
            )
            return ""
        
    def _calculate_capability_confidence(self, message: Message, capability: AgentCapability) -> float:
        """
        Calcola la confidenza per una specifica capacità.
        
        Args:
            message: Messaggio da valutare
            capability: Capacità da testare
            
        Returns:
            Confidenza (0.0-1.0) per questa capacità
        """
        content_lower = message.content.lower()
        keyword_matches = 0
        
        for keyword in capability.keywords:
            if keyword.lower() in content_lower:
                keyword_matches += 1
                
        if not capability.keywords:
            return 0.0
            
        base_confidence = keyword_matches / len(capability.keywords)
        
        # Aggiusta la confidenza basandosi sul contesto e metadati
        context_boost = self._get_context_boost(message, capability)
        
        return min(1.0, base_confidence + context_boost)

    def _get_context_boost(self, message: Message, capability: AgentCapability) -> float:
        """
        Calcola un boost di confidenza basato sul contesto della conversazione.
        
        Args:
            message: Messaggio corrente
            capability: Capacità da valutare
            
        Returns:
            Boost di confidenza (-0.3 a +0.3)
        """
        # Implementazione base - da estendere negli agenti specifici
        return 0.0

    @abstractmethod
    async def process_request(self, message: Message) -> Message:
        """
        Processa una richiesta dell'utente.
        
        Args:
            message: Messaggio da processare
            
        Returns:
            AgentResponse con il risultato del processamento
        """
        pass

    @abstractmethod
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Restituisce informazioni sull'agente.
        
        Returns:
            Dizionario con informazioni sull'agente (nome, capacità, stato, ecc.)
        """
        pass

    async def initialize(self):
        """
        Inizializza l'agente (connessioni API, risorse, ecc.).
        Da implementare negli agenti che richiedono inizializzazione asincrona.
        """
        self.is_active = True

    async def shutdown(self):
        """
        Chiude l'agente e libera le risorse.
        """
        self.is_active = False
        
        # Deregistra dal message broker
        try:
            self.message_consumer.unsubscribe(f"agent.{self.agent_name}")
        except Exception as e:
            self.logger.error(f"Errore nella deregistrazione dal message broker: {e}")
            

    def get_context(self, conversation_id: str, max_messages: int = 10) -> List[Message]:
        """
        Recupera il contesto della conversazione.
        
        Args:
            conversation_id: ID della conversazione
            max_messages: Numero massimo di messaggi da recuperare
            
        Returns:
            Lista di messaggi del contesto
        """
        try:
            return self.memory_manager.get_conversation_history(
                conversation_id, 
                limit=max_messages
            )
        except Exception as e:
            self.logger.error(f"Errore nel recupero del contesto: {e}")
            return []

    def save_to_memory(self, conversation_id: str, message: Message):
        """
        Salva un messaggio nella memoria.
        
        Args:
            conversation_id: ID della conversazione
            message: Messaggio da salvare
        """
        try:
            self.memory_manager.save_message(conversation_id, message)
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio in memoria: {e}")

    def update_metrics(self, processing_time: float, success: bool):
        """
        Aggiorna le metriche di performance dell'agente.
        
        Args:
            processing_time: Tempo di processamento in secondi
            success: Se la richiesta è stata processata con successo
        """
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            
        # Calcola media mobile del tempo di processamento
        if self.total_requests == 1:
            self.average_processing_time = processing_time
        else:
            alpha = 0.1  # Fattore di smoothing
            self.average_processing_time = (
                alpha * processing_time + 
                (1 - alpha) * self.average_processing_time
            )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Restituisce le metriche di performance dell'agente.
        
        Returns:
            Dizionario con le metriche di performance
        """
        success_rate = (
            self.successful_requests / self.total_requests 
            if self.total_requests > 0 else 0.0
        )
        
        return {
            "agent_name": self.agent_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": success_rate,
            "average_processing_time": self.average_processing_time,
            "is_active": self.is_active
        }

    def validate_request(self, message: Message) -> bool:
        """
        Valida una richiesta prima del processamento.
        
        Args:
            message: Messaggio da validare
            
        Returns:
            True se la richiesta è valida, False altrimenti
        """
        if not message or not message.content:
            return False
            
        if len(message.content) > self.max_context_length:
            self.logger.warning(f"Messaggio troppo lungo: {len(message.content)} caratteri")
            return False
            
        return True

    async def execute_with_timeout(self, coro, timeout: Optional[float] = None):
        """
        Esegue una coroutine con timeout.
        
        Args:
            coro: Coroutine da eseguire
            timeout: Timeout in secondi (usa default dell'agente se None)
            
        Returns:
            Risultato della coroutine
            
        Raises:
            asyncio.TimeoutError: Se il timeout viene superato
        """
        timeout = timeout or self.processing_timeout
        return await asyncio.wait_for(coro, timeout=timeout)

    def __str__(self) -> str:
        return f"BaseAgent(name={self.agent_name}, capabilities={len(self.capabilities)})"

    def __repr__(self) -> str:
        return (f"BaseAgent(agent_name='{self.agent_name}', "
                f"capabilities={self.capabilities}, "
                f"is_active={self.is_active})")


# Decorator per registrazione automatica degli agenti
def register_agent(agent_class):
    """
    Decorator per registrare automaticamente un agente nel sistema.
    
    Usage:
        @register_agent
        class WeatherAgent(BaseAgent):
            pass
    """
    # Questa implementazione verrà completata nel AgentManager
    agent_class._is_registered = True
    return agent_class