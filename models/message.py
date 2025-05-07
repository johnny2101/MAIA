# models/message.py
from datetime import datetime, UTC
from typing import Dict, Optional, Any, Union, List
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class SenderType(str, Enum):
    """Enumera i possibili tipi di mittenti per un messaggio."""
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"


class MessageRole(str, Enum):
    """Definisce i ruoli possibili per un messaggio, simile al formato di OpenAI."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"


class MessageStatus(str, Enum):
    """Stati possibili di un messaggio durante il suo ciclo di vita."""
    CREATED = "created"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class Intent(BaseModel):
    """Rappresenta un intento rilevato nel messaggio."""
    name: str
    confidence: float
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """
    Rappresenta un singolo messaggio nel sistema MAIA.
    Può essere un messaggio dell'utente, una risposta del sistema,
    o una comunicazione interna tra agenti.
    """
    id: UUID = Field(default_factory=uuid4)
    content: str
    sender_id: str
    sender_type: SenderType
    role: MessageRole
    conversation_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: MessageStatus = MessageStatus.CREATED
    
    # Metadati aggiuntivi
    agent_id: Optional[str] = None  # ID dell'agente che ha gestito il messaggio
    parent_message_id: Optional[UUID] = None  # ID del messaggio a cui questo risponde
    intents: List[Intent] = Field(default_factory=list)  # Intenti rilevati nel messaggio
    confidence: Optional[float] = None  # Livello di confidenza nella risposta
    processing_time: Optional[float] = None  # Tempo di elaborazione in ms
    tokens_used: Optional[int] = None  # Numero di token utilizzati (per LLM)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Metadati aggiuntivi specifici
    
    # Metodi utili
    def add_intent(self, name: str, confidence: float, parameters: Dict[str, Any] = None):
        """Aggiunge un intento rilevato al messaggio."""
        if parameters is None:
            parameters = {}
        self.intents.append(Intent(name=name, confidence=confidence, parameters=parameters))
    
    def mark_as_processing(self):
        """Marca il messaggio come in fase di elaborazione."""
        self.status = MessageStatus.PROCESSING
        return self
    
    def mark_as_delivered(self):
        """Marca il messaggio come consegnato."""
        self.status = MessageStatus.DELIVERED
        return self
    
    def mark_as_failed(self):
        """Marca il messaggio come fallito."""
        self.status = MessageStatus.FAILED
        return self
    
    def mark_as_read(self):
        """Marca il messaggio come letto."""
        self.status = MessageStatus.READ
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte il messaggio in un dizionario."""
        return self.dict()
    
    def to_llm_format(self) -> Dict[str, str]:
        """
        Converte il messaggio nel formato utilizzato dalle API degli LLM
        (es. formato OpenAI o simile).
        """
        return {
            "role": self.role,
            "content": self.content
        }
    
    @classmethod
    def create_user_message(cls, content: str, user_id: str, conversation_id: UUID) -> "Message":
        """Factory method per creare rapidamente un messaggio utente."""
        return cls(
            content=content,
            sender_id=user_id,
            sender_type=SenderType.USER,
            role=MessageRole.USER,
            conversation_id=conversation_id
        )
    
    @classmethod
    def create_system_message(cls, content: str, conversation_id: UUID) -> "Message":
        """Factory method per creare rapidamente un messaggio di sistema."""
        return cls(
            content=content,
            sender_id="system",
            sender_type=SenderType.SYSTEM,
            role=MessageRole.SYSTEM,
            conversation_id=conversation_id
        )
    
    @classmethod
    def create_agent_message(cls, content: str, agent_id: str, conversation_id: UUID) -> "Message":
        """Factory method per creare rapidamente un messaggio di un agente."""
        return cls(
            content=content,
            sender_id=agent_id,
            sender_type=SenderType.AGENT,
            role=MessageRole.ASSISTANT,
            agent_id=agent_id,
            conversation_id=conversation_id
        )