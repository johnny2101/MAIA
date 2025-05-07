# models/conversation.py
from datetime import UTC, datetime
from typing import Dict, Optional, Any, List, Set
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field


class ConversationStatus(str, Enum):
    """Stati possibili di una conversazione."""
    ACTIVE = "active"         # Conversazione in corso
    PAUSED = "paused"         # Conversazione in pausa
    COMPLETED = "completed"   # Conversazione completata
    ARCHIVED = "archived"     # Conversazione archiviata
    DELETED = "deleted"       # Conversazione eliminata (soft delete)


class ConversationTag(BaseModel):
    """Tag per organizzare e cercare le conversazioni."""
    name: str
    color: Optional[str] = None  # Colore del tag (es. "#FF5733")


class Conversation(BaseModel):
    """
    Rappresenta una sessione di conversazione tra un utente e MAIA.
    Contiene metadati sulla conversazione e riferimenti ai messaggi.
    """
    id: UUID = Field(default_factory=uuid4)
    title: str
    user_id: UUID
    
    # Metadati
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: ConversationStatus = ConversationStatus.ACTIVE
    
    # Organizzazione
    tags: List[ConversationTag] = Field(default_factory=list)
    is_pinned: bool = False
    is_favorite: bool = False
    
    # Contenuto e metriche
    summary: Optional[str] = None  # Breve riassunto della conversazione
    last_message_id: Optional[UUID] = None  # ID dell'ultimo messaggio
    last_user_message_id: Optional[UUID] = None  # ID dell'ultimo messaggio dell'utente
    last_message_timestamp: Optional[datetime] = None
    message_count: int = 0
    
    # Connessioni agli agenti
    active_agents: Set[str] = Field(default_factory=set)  # ID degli agenti attivi in questa conversazione
    agent_states: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # Stato per ciascun agente
    
    # Dati aggiuntivi
    context: Dict[str, Any] = Field(default_factory=dict)  # Dati di contesto della conversazione
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Metadati aggiuntivi
    
    # Metodi di utilità
    def update_timestamp(self):
        """Aggiorna il timestamp dell'ultima modifica."""
        self.updated_at = datetime.now(UTC)
    
    def add_message(self, message_id: UUID, is_user: bool, timestamp: Optional[datetime] = None):
        """
        Aggiorna i metadati dopo l'aggiunta di un nuovo messaggio.
        """
        self.message_count += 1
        self.last_message_id = message_id
        self.last_message_timestamp = timestamp or datetime.now(UTC)
        
        if is_user:
            self.last_user_message_id = message_id
            
        self.update_timestamp()
    
    def set_title(self, title: str):
        """Aggiorna il titolo della conversazione."""
        self.title = title
        self.update_timestamp()
    
    def set_summary(self, summary: str):
        """Imposta o aggiorna il riassunto della conversazione."""
        self.summary = summary
        self.update_timestamp()
    
    def add_tag(self, name: str, color: Optional[str] = None):
        """Aggiunge un tag alla conversazione."""
        for tag in self.tags:
            if tag.name.lower() == name.lower():
                # Il tag esiste già, aggiorna solo il colore se specificato
                if color:
                    tag.color = color
                return
                
        # Aggiungi nuovo tag
        self.tags.append(ConversationTag(name=name, color=color))
        self.update_timestamp()
    
    def remove_tag(self, name: str):
        """Rimuove un tag dalla conversazione."""
        self.tags = [tag for tag in self.tags if tag.name.lower() != name.lower()]
        self.update_timestamp()
    
    def mark_as_completed(self):
        """Marca la conversazione come completata."""
        self.status = ConversationStatus.COMPLETED
        self.update_timestamp()
    
    def mark_as_archived(self):
        """Archivia la conversazione."""
        self.status = ConversationStatus.ARCHIVED
        self.update_timestamp()
    
    def reactivate(self):
        """Riattiva una conversazione archiviata o completata."""
        self.status = ConversationStatus.ACTIVE
        self.update_timestamp()
    
    def add_active_agent(self, agent_id: str):
        """Registra un agente come attivo in questa conversazione."""
        self.active_agents.add(agent_id)
        if agent_id not in self.agent_states:
            self.agent_states[agent_id] = {}
        self.update_timestamp()
    
    def remove_active_agent(self, agent_id: str):
        """Rimuove un agente dagli agenti attivi."""
        if agent_id in self.active_agents:
            self.active_agents.remove(agent_id)
        self.update_timestamp()
    
    def update_agent_state(self, agent_id: str, state: Dict[str, Any]):
        """Aggiorna lo stato di un agente per questa conversazione."""
        if agent_id not in self.agent_states:
            self.agent_states[agent_id] = {}
        
        self.agent_states[agent_id].update(state)
        self.update_timestamp()
    
    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Recupera lo stato corrente di un agente."""
        return self.agent_states.get(agent_id, {})
    
    def set_context(self, key: str, value: Any):
        """Imposta un valore nel contesto della conversazione."""
        self.context[key] = value
        self.update_timestamp()
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Recupera un valore dal contesto della conversazione."""
        return self.context.get(key, default)
    
    @classmethod
    def create_new(cls, user_id: UUID, title: Optional[str] = None) -> "Conversation":
        """Factory method per creare una nuova conversazione."""
        return cls(
            title=title or "Nuova conversazione",
            user_id=user_id
        )


class ConversationRepository:
    """
    Classe per interagire con l'archivio delle conversazioni.
    Questa è una semplice rappresentazione che dovrà essere implementata
    con un database reale (PostgreSQL, MongoDB, ecc.).
    """
    
    async def find_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """Trova una conversazione per ID."""
        # Implementazione con database reale
        pass
    
    async def find_by_user(self, user_id: UUID, 
                           limit: int = 10, 
                           offset: int = 0,
                           status: Optional[ConversationStatus] = None,
                           search_term: Optional[str] = None,
                           tags: Optional[List[str]] = None) -> List[Conversation]:
        """Trova conversazioni di un utente con filtri vari."""
        # Implementazione con database reale
        pass
    
    async def create(self, conversation: Conversation) -> Conversation:
        """Crea una nuova conversazione."""
        # Implementazione con database reale
        pass
    
    async def update(self, conversation: Conversation) -> Conversation:
        """Aggiorna una conversazione esistente."""
        # Implementazione con database reale
        pass
    
    async def delete(self, conversation_id: UUID) -> bool:
        """Elimina una conversazione (soft delete)."""
        # Implementazione con database reale
        pass
    
    async def get_active_conversations(self, user_id: UUID) -> List[Conversation]:
        """Ottiene le conversazioni attive di un utente."""
        # Implementazione con database reale
        pass