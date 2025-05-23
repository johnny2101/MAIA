from typing import Dict, List, Any, Optional
from models.conversation import Conversation, ConversationStatus, ConversationTag
from models.message import Message, SenderType
from datetime import datetime, UTC

class MemoryManager:
    """
    Gestisce lo stato delle conversazioni e il contesto.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza il MemoryManager con la configurazione specificata.
        
        Args:
            config: Configurazione per il MemoryManager
        """
        self._config = config
        self._db_client = None  # Client per il database
        self._cache = {}  # Cache in memoria per conversazioni attive
    
    def initialize_conversation(self, user_id: str) -> str:
        """
        Inizializza una nuova conversazione per un utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            ID della conversazione
        """
        conversation = Conversation.create_new(
            user_id = user_id, 
            title="test_conversation"
        )
        
        self._cache[conversation.id] = conversation
        
        return conversation.id
    
    def add_message(self, conversation_id: str, message: Message) -> bool:
        """
        Aggiunge un messaggio a una conversazione.
        
        Args:
            conversation_id: ID della conversazione
            message: Messaggio da aggiungere
            
        Returns:
            True se l'aggiunta ha avuto successo
        """
        
        try:
            if conversation_id in self._cache:
                conversation: Conversation = self._cache[conversation_id] 
                conversation.add_message(message.id, is_user= message.sender_type == SenderType.USER)
                self._cache[conversation_id] = conversation
                return True
        except:
            return False
        
    
    def get_conversation_history(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Recupera la cronologia di una conversazione.
        
        Args:
            conversation_id: ID della conversazione
            limit: Numero massimo di messaggi da recuperare
            
        Returns:
            Lista di messaggi nella conversazione
        """
        pass
    
    def get_relevant_context(self, conversation_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Recupera il contesto rilevante per una query.
        
        Args:
            conversation_id: ID della conversazione
            query: Query per cui recuperare il contesto
            
        Returns:
            Lista di messaggi rilevanti come contesto
        """
        pass
    
    def save_state(self, conversation_id: str, state: Dict[str, Any]) -> bool:
        """
        Salva lo stato di una conversazione.
        
        Args:
            conversation_id: ID della conversazione
            state: Stato da salvare
            
        Returns:
            True se il salvataggio ha avuto successo
        """
        pass
    
    def load_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Carica lo stato di una conversazione.
        
        Args:
            conversation_id: ID della conversazione
            
        Returns:
            Stato della conversazione o None se non trovato
        """
        pass
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Cancella una conversazione.
        
        Args:
            conversation_id: ID della conversazione da cancellare
            
        Returns:
            True se la cancellazione ha avuto successo
        """
        pass