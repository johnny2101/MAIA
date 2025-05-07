from datetime import datetime, timedelta, UTC
from typing import Dict, Optional, Any, List, Union
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Stati possibili di un task."""
    PENDING = "pending"       # Task in attesa di esecuzione
    RUNNING = "running"       # Task in esecuzione
    COMPLETED = "completed"   # Task completato con successo
    FAILED = "failed"         # Task fallito
    CANCELLED = "cancelled"   # Task annullato
    TIMEOUT = "timeout"       # Task terminato per timeout


class TaskPriority(int, Enum):
    """Priorità possibili per i task."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskResult(BaseModel):
    """Risultato dell'esecuzione di un task."""
    success: bool
    data: Optional[Any] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    execution_time: Optional[float] = None  # Tempo di esecuzione in millisecondi


class Task(BaseModel):
    """
    Rappresenta un'attività da eseguire all'interno del sistema MAIA.
    Può essere una chiamata API, un'elaborazione LLM, un'operazione di database, ecc.
    """
    id: UUID = Field(default_factory=uuid4)
    type: str  # Tipo di task (es. "llm_call", "api_call", "db_operation")
    name: str  # Nome del task per logging e monitoraggio
    agent_id: Optional[str] = None  # ID dell'agente che ha creato il task
    conversation_id: Optional[UUID] = None  # ID conversazione associata
    message_id: Optional[UUID] = None  # ID messaggio associato
    user_id: Optional[UUID] = None  # ID utente associato
    
    # Priorità e scheduling
    priority: TaskPriority = TaskPriority.NORMAL
    scheduled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timeout: Optional[float] = None  # Timeout in secondi
    max_retries: int = 0
    retry_count: int = 0
    
    # Stato di esecuzione
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Contenuto del task
    payload: Dict[str, Any] = Field(default_factory=dict)  # Dati necessari per l'esecuzione
    result: Optional[TaskResult] = None  # Risultato dell'esecuzione
    
    # Tracciamento e debug
    logs: List[str] = Field(default_factory=list)
    parent_task_id: Optional[UUID] = None  # Per task annidati/dipendenti
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Metodi di utilità
    def mark_as_running(self):
        """Marca il task come in esecuzione."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(UTC)
    
    def mark_as_completed(self, result_data: Any = None, execution_time: Optional[float] = None):
        """Marca il task come completato con successo."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.result = TaskResult(
            success=True,
            data=result_data,
            execution_time=execution_time
        )
    
    def mark_as_failed(self, error_message: str, error_type: Optional[str] = None, 
                      execution_time: Optional[float] = None):
        """Marca il task come fallito."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(UTC)
        self.result = TaskResult(
            success=False,
            error_message=error_message,
            error_type=error_type,
            execution_time=execution_time
        )
    
    def mark_as_cancelled(self, reason: Optional[str] = None):
        """Annulla il task."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(UTC)
        self.result = TaskResult(
            success=False,
            error_message=f"Task cancelled: {reason}" if reason else "Task cancelled"
        )
    
    def mark_as_timeout(self):
        """Marca il task come terminato per timeout."""
        self.status = TaskStatus.TIMEOUT
        self.completed_at = datetime.now(UTC)
        self.result = TaskResult(
            success=False,
            error_message="Task execution timed out",
            error_type="timeout"
        )
    
    def should_retry(self) -> bool:
        """Determina se il task deve essere ritentato."""
        return (self.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT] and 
                self.retry_count < self.max_retries)
    
    def increment_retry(self):
        """Incrementa il contatore dei tentativi e resetta lo stato."""
        self.retry_count += 1
        self.status = TaskStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.result = None
    
    def add_log(self, message: str):
        """Aggiunge una riga di log al task."""
        timestamp = datetime.now(UTC).isoformat()
        self.logs.append(f"[{timestamp}] {message}")
    
    def is_expired(self) -> bool:
        """Verifica se il task è scaduto (oltre il timeout)."""
        if not self.timeout or not self.started_at:
            return False
        
        expiration_time = self.started_at + timedelta(seconds=self.timeout)
        return datetime.now(UTC) > expiration_time
    
    @classmethod
    def create_llm_task(cls, prompt: str, model: str, agent_id: Optional[str] = None,
                      conversation_id: Optional[UUID] = None, message_id: Optional[UUID] = None,
                      priority: TaskPriority = TaskPriority.NORMAL) -> "Task":
        """Factory method per creare un task di chiamata LLM."""
        return cls(
            type="llm_call",
            name=f"LLM Call ({model})",
            agent_id=agent_id,
            conversation_id=conversation_id,
            message_id=message_id,
            priority=priority,
            payload={
                "prompt": prompt,
                "model": model,
                "max_tokens": 1000,  # Default, sovrascrivibile
                "temperature": 0.7   # Default, sovrascrivibile
            }
        )
    
    @classmethod
    def create_api_task(cls, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None,
                       agent_id: Optional[str] = None, conversation_id: Optional[UUID] = None,
                       priority: TaskPriority = TaskPriority.NORMAL) -> "Task":
        """Factory method per creare un task di chiamata API."""
        return cls(
            type="api_call",
            name=f"API Call ({endpoint})",
            agent_id=agent_id,
            conversation_id=conversation_id,
            priority=priority,
            payload={
                "endpoint": endpoint,
                "method": method,
                "data": data or {},
                "headers": {}  # Default, sovrascrivibile
            }
        )


class TaskRepository:
    """
    Classe per interagire con l'archivio dei task.
    Questa è una semplice rappresentazione che dovrà essere implementata
    con un database reale e un sistema di code (come Redis/RabbitMQ).
    """
    
    async def find_by_id(self, task_id: UUID) -> Optional[Task]:
        """Trova un task per ID."""
        # Implementazione con database reale
        pass
    
    async def find_pending_tasks(self, agent_id: Optional[str] = None, 
                               limit: int = 10) -> List[Task]:
        """Trova task in attesa di esecuzione."""
        # Implementazione con database reale
        pass
    
    async def create(self, task: Task) -> Task:
        """Crea un nuovo task e lo inserisce nella coda appropriata."""
        # Implementazione con database reale + message broker
        pass
    
    async def update(self, task: Task) -> Task:
        """Aggiorna un task esistente."""
        # Implementazione con database reale
        pass
    
    async def delete(self, task_id: UUID) -> bool:
        """Elimina un task."""
        # Implementazione con database reale
        pass
    
    async def get_tasks_by_conversation(self, conversation_id: UUID) -> List[Task]:
        """Ottiene i task associati a una conversazione."""
        # Implementazione con database reale
        pass
    
    async def get_tasks_by_agent(self, agent_id: str, 
                               status: Optional[Union[TaskStatus, List[TaskStatus]]] = None) -> List[Task]:
        """Ottiene i task associati a un agente."""
        # Implementazione con database reale
        pass