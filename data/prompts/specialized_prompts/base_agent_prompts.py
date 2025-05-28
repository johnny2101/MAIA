class BaseAgentPrompts:
    """
    Base class for agent prompts.
    This class provides a template for specialized agent prompts.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.prompts = {
        }

    def get_prompt(self) -> str:
        """
        Returns the base prompt for the agent.
        """
        return f"Hello, I am {self.agent_name}, your specialized agent."
    
    def get_specialized_prompt(self, specialization: str) -> str:
        """
        Returns a specialized prompt based on the agent's specialization.
        """
        return self.prompts.get(specialization,"")