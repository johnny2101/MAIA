import json
import time
from agents.base_agent import BaseAgent, AgentCapability
from integrations.search_engine import WebResearchAssistant
from data.prompts.specialized_prompts.web_agent_prompts import WebAgentPrompts

class WebAgent(BaseAgent):
    """
    Classe per l'agente web che estende BaseAgent.
    Questa classe è responsabile della gestione delle operazioni web come la ricerca e l'analisi dei risultati.
    """

    def __init__(self, agent_name: str = "WebAgent", capabilities=None, memory_manager=None):
        super().__init__(agent_name=agent_name, capabilities=capabilities, memory_manager=memory_manager)
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        #self.api_key = "YOUR_API_KEY"  # Sostituisci con la tua API key
        #self.search_engine_id = "YOUR_SEARCH_ENGINE_ID"  # Sostituisci con il tuo Search Engine ID
        self.web_research_integration = WebResearchAssistant()
        self.prompts = WebAgentPrompts(agent_name=agent_name)
        
    def get_agent_info(self):
        """
        Returns a dictionary with information about the agent.
        :return: Dictionary containing agent's name, description, and capabilities.
        """
        return {
            "name": self.agent_name,
            "description": "Agente web per la ricerca e l'analisi dei risultati.",
            "capabilities": [
                "Eseguire ricerche su Google",
                "Analizzare i risultati della ricerca",
                "Gestire le operazioni web"
            ]
        }

    def process_request(self, message):
        """
        Processa una richiesta web.
        :param message: Il messaggio da elaborare.
        :return: Risposta elaborata.
        """
        # Implementa la logica per processare la richiesta
        # Ad esempio, effettuare una ricerca su Google e restituire i risultati
        #print( f"Elaborazione della richiesta: {message}")
        context = message.get("context_to_forward", "cosa vuol dire flamingo?")
        print(f"Context to forward: {context}")
        #self.web_research_integration.research_topic(message.get("context_to_forward", "cosa vuol dire flamingo"))
        try:
            prompt = self.prompts.get_web_search_prompt().format(context)
        except KeyError as e:
            print(f"Error retrieving prompt: {e}")
            return "Error retrieving prompt"
        #save prompt to file 
        with open("web_search_prompt.txt", "w") as file:
            file.write(prompt)
        search_query = json.loads(self.qwery_llm(prompt,""))
        query = search_query.get("query", "cosa vuol dire flamingo?")
        print(f"Search query: {query}")
        research_results = self.web_research_integration.research_topic(query, num_sources=1)
        #print(f"Research results type: {type(research_results)} - length: {len(research_results)}\n {research_results}")
        useful_results = []
        for result in research_results["sources"]:
            content = result["content"]
            prompt = self.prompts.get_content_filtering_prompt().format(context, content)
            is_content_useful = json.loads(self.qwery_llm(prompt, "")).get("is_useful", False)
            if content and is_content_useful:
                useful_results.append(content)
        
        print(f"Useful results: {useful_results}")
        
        summary_prompt = self.prompts.get_web_analysis_prompt().format(context, useful_results)
        
        final_response = self.qwery_llm(summary_prompt, "")
        print(f"Final response: {final_response}")
        payload = {
                    "chat_id": 441992716,
                    "text": final_response,
                }
        if final_response != "":
            self.message_publisher.publish("user.message.processed", json.dumps(payload))
        #save research results to file
        
    
if __name__ == "__main__":
    # Esempio di utilizzo dell'agente web
    capabilities = AgentCapability(
        name="WebAgent",
        description="Capacità dell'agente web per la ricerca e l'analisi dei risultati.",
        keywords=["web", "search", "analysis"]
    )
    web_agent = WebAgent(capabilities=capabilities)
    try:
        while True:
            time.sleep(1)
        
    except KeyboardInterrupt:
        print("Interruzione dell'agente web.")
    print(f"Agente creato: {web_agent.agent_name}")
    