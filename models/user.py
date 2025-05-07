# models/user.py
from datetime import datetime, UTC
from typing import Dict, Optional, Any, List
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    """Ruoli utente per gestire permessi e accessi."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserStatus(str, Enum):
    """Stati possibili dell'account utente."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    PENDING = "pending"


class AgentPreference(BaseModel):
    """Preferenze specifiche per un agente."""
    agent_id: str
    enabled: bool = True
    priority: int = 1  # Priorità più alta = agente preferito
    custom_settings: Dict[str, Any] = Field(default_factory=dict)


class User(BaseModel):
    """
    Rappresenta un utente del sistema MAIA.
    Memorizza informazioni personali, preferenze e impostazioni.
    """
    id: UUID = Field(default_factory=uuid4)
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    
    # Informazioni account
    password_hash: Optional[str] = None  # Solo hash, mai password in chiaro
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login: Optional[datetime] = None
    
    # Preferenze e impostazioni
    language: str = "it"  # Lingua preferita
    timezone: str = "Europe/Rome"  # Fuso orario
    agent_preferences: List[AgentPreference] = Field(default_factory=list)
    
    # Informazioni contestuali e personalizzazione
    contexts: Dict[str, Any] = Field(default_factory=dict)  # Informazioni persistenti per personalizzazione
    session_data: Dict[str, Any] = Field(default_factory=dict)  # Dati temporanei di sessione
    
    # Limitazioni e usage
    api_key: Optional[str] = None  # Per accesso API
    api_usage: Dict[str, int] = Field(default_factory=dict)  # Tracciamento utilizzo
    max_conversations: int = 100  # Limite conversazioni salvate
    
    # Metodi per gestione preferenze
    def update_agent_preference(self, agent_id: str, enabled: bool = True, 
                               priority: int = None, settings: Dict[str, Any] = None):
        """Aggiorna le preferenze per un agente specifico."""
        # Cerca se esiste già una preferenza per questo agente
        for i, pref in enumerate(self.agent_preferences):
            if pref.agent_id == agent_id:
                self.agent_preferences[i].enabled = enabled
                if priority is not None:
                    self.agent_preferences[i].priority = priority
                if settings is not None:
                    self.agent_preferences[i].custom_settings.update(settings)
                return
        
        # Se non esiste, crea una nuova preferenza
        new_pref = AgentPreference(
            agent_id=agent_id,
            enabled=enabled,
            priority=priority if priority is not None else 1,
            custom_settings=settings or {}
        )
        self.agent_preferences.append(new_pref)
    
    def get_agent_preference(self, agent_id: str) -> Optional[AgentPreference]:
        """Ottiene le preferenze per un agente specifico."""
        for pref in self.agent_preferences:
            if pref.agent_id == agent_id:
                return pref
        return None
    
    def disable_agent(self, agent_id: str):
        """Disabilita un agente specifico per questo utente."""
        self.update_agent_preference(agent_id, enabled=False)
    
    def enable_agent(self, agent_id: str):
        """Abilita un agente specifico per questo utente."""
        self.update_agent_preference(agent_id, enabled=True)
    
    def set_context(self, key: str, value: Any):
        """Imposta un valore di contesto persistente."""
        self.contexts[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Ottiene un valore di contesto."""
        return self.contexts.get(key, default)
    
    def set_session_data(self, key: str, value: Any):
        """Imposta un dato temporaneo di sessione."""
        self.session_data[key] = value
    
    def get_session_data(self, key: str, default: Any = None) -> Any:
        """Ottiene un dato temporaneo di sessione."""
        return self.session_data.get(key, default)
    
    def clear_session_data(self):
        """Pulisce tutti i dati temporanei di sessione."""
        self.session_data = {}
    
    def track_api_usage(self, endpoint: str, tokens: int = 1):
        """Tiene traccia dell'utilizzo dell'API."""
        if endpoint not in self.api_usage:
            self.api_usage[endpoint] = 0
        self.api_usage[endpoint] += tokens
    
    def reset_api_usage(self):
        """Resetta il conteggio dell'utilizzo dell'API."""
        self.api_usage = {}
    
    def update_last_login(self):
        """Aggiorna il timestamp dell'ultimo login."""
        self.last_login = datetime.utcnow()
    
    @classmethod
    def create_new_user(cls, username: str, email: Optional[str] = None, 
                        full_name: Optional[str] = None) -> "User":
        """Factory method per creare un nuovo utente."""
        return cls(
            username=username,
            email=email,
            full_name=full_name
        )


class UserRepository:
    """
    Classe per interagire con l'archivio utenti.
    Questa è una semplice rappresentazione che dovrà essere implementata
    con un database reale (PostgreSQL, MongoDB, ecc.).
    """
    
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Trova un utente per ID."""
        # Implementazione con database reale
        pass
    
    async def find_by_username(self, username: str) -> Optional[User]:
        """Trova un utente per username."""
        # Implementazione con database reale
        pass
    
    async def find_by_email(self, email: str) -> Optional[User]:
        """Trova un utente per email."""
        # Implementazione con database reale
        pass
    
    async def create(self, user: User) -> User:
        """Crea un nuovo utente."""
        # Implementazione con database reale
        pass
    
    async def update(self, user: User) -> User:
        """Aggiorna un utente esistente."""
        # Implementazione con database reale
        pass
    
    async def delete(self, user_id: UUID) -> bool:
        """Elimina un utente."""
        # Implementazione con database reale
        pass