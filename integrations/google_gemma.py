"""
Google Gemma API Integration Module for MAIA

This module provides a client for interacting with Google's Gemma models
through the Vertex AI API or the model's specific endpoints.

Usage:
    from integrations.google_gemma_api import GemmaClient
    
    client = GemmaClient()
    response = await client.generate_text("What is the weather like today?")
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Optional, Union, Any

import aiohttp
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.cloud import aiplatform
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from utils.logger import get_logger
from utils.config import get_config
from models.message import Message

logger = get_logger(__name__)

class GemmaClient:
    """Client for interacting with Google's Gemma models through Vertex AI API."""
    
    def __init__(
        self,
        model_name: str = "gemma3-12b-it",
        project_id: Optional[str] = None,
        location: str = "us-central1",
        credentials_path: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 60,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
        top_p: float = 0.95,
        top_k: int = 40,
    ):
        """
        Initialize the Gemma client.
        
        Args:
            model_name: The Gemma model name to use (e.g., "gemma-7b-it", "gemma-27b")
            project_id: Google Cloud project ID. If None, will use the default from environment
            location: Google Cloud region
            credentials_path: Path to service account credentials JSON file.
                              If None, will use default credentials
            max_retries: Maximum number of retries for API calls
            timeout: Timeout in seconds for API calls
            temperature: Sampling temperature for generation (0.0 to 1.0)
            max_output_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter (0.0 to 1.0)
            top_k: Number of highest probability tokens to consider for generation
        """
        self.model_name = model_name
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or get_config().GOOGLE_CLOUD_PROJECT
        self.location = location
        self.credentials_path = credentials_path
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Generation parameters
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.top_p = top_p
        self.top_k = top_k
        
        # Initialize credentials and client
        self._initialize_client()
        
        logger.info(f"Initialized GemmaClient with model: {model_name}")
    
    def _initialize_client(self) -> None:
        """Initialize the Vertex AI client with appropriate credentials."""
        try:
            # Set up credentials
            if self.credentials_path:
                self.credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            else:
                self.credentials, self.project_id = google.auth.default()
            
            # Initialize Vertex AI
            aiplatform.init(
                project=self.project_id,
                location=self.location,
                credentials=self.credentials
            )
            
            # Get the model endpoint
            self.model_endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_name}"
            
            logger.debug(f"Successfully initialized Vertex AI client with endpoint: {self.model_endpoint}")
        
        except Exception as e:
            logger.error(f"Failed to initialize Gemma client: {str(e)}")
            raise
    
    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        safety_settings: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate text using the Gemma model.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt to guide model behavior
            temperature: Sampling temperature (0.0 to 1.0)
            max_output_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter (0.0 to 1.0)
            top_k: Number of highest probability tokens to consider
            safety_settings: List of safety settings to apply
            
        Returns:
            Dictionary containing the model response and metadata
        """
        start_time = time.time()
        
        # Use instance defaults if not provided
        temperature = temperature if temperature is not None else self.temperature
        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.max_output_tokens
        top_p = top_p if top_p is not None else self.top_p
        top_k = top_k if top_k is not None else self.top_k
        
        try:
            # Create the parameter dictionary
            parameters = {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "topP": top_p,
                "topK": top_k,
            }
            
            # Add safety settings if provided
            if safety_settings:
                parameters["safetySettings"] = safety_settings
            
            # Construct the request payload
            instance = {
                "prompt": prompt,
            }
            
            # Add system prompt if provided
            if system_prompt:
                instance["system_prompt"] = system_prompt
            
            # Create PredictionServiceClient
            client = aiplatform.gapic.PredictionServiceClient(credentials=self.credentials)
            
            # Make the prediction request
            response = await asyncio.to_thread(
                client.predict,
                endpoint=self.model_endpoint,
                instances=[instance],
                parameters=parameters,
            )
            
            # Process and return the response
            result = {
                "text": response.predictions[0]["text"],
                "metadata": {
                    "model": self.model_name,
                    "latency_ms": round((time.time() - start_time) * 1000),
                }
            }
            
            if hasattr(response.predictions[0], "safetyAttributes"):
                result["safety_attributes"] = response.predictions[0]["safetyAttributes"]
            
            if hasattr(response.predictions[0], "tokenCount"):
                result["metadata"]["token_count"] = response.predictions[0]["tokenCount"]
            
            logger.debug(f"Generated text with Gemma (length: {len(result['text'])})")
            return result
            
        except Exception as e:
            logger.error(f"Error generating text with Gemma: {str(e)}")
            raise
    
    async def analyze_intent(self, user_message: str, conversation_history: List[Message] = None) -> Dict[str, Any]:
        """
        Analyze the intent of a user message using Gemma.
        
        Args:
            user_message: The user's message text
            conversation_history: Optional list of previous messages for context
            
        Returns:
            Dictionary containing the detected intent, confidence, and other metadata
        """
        # Build the prompt for intent detection
        prompt = self._build_intent_detection_prompt(user_message, conversation_history)
        
        # Get response from model with lower temperature for more deterministic results
        response = await self.generate_text(
            prompt=prompt,
            temperature=0.2,  # Lower temperature for more deterministic results
            max_output_tokens=512  # Shorter response needed for intent classification
        )
        
        # Parse the response to extract intent information
        try:
            # The response should be in JSON format
            intent_data = json.loads(response["text"])
            return intent_data
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse intent response as JSON: {response['text']}")
            # Return a fallback intent with low confidence
            return {
                "primary_intent": "unknown",
                "confidence": 0.3,
                "entities": {},
                "requires_clarification": True
            }
    
    async def route_request(self, user_message: str, available_agents: List[str], conversation_history: List[Message] = None) -> Dict[str, Any]:
        """
        Determine which agent should handle a user request.
        
        Args:
            user_message: The user's message text
            available_agents: List of available agent names
            conversation_history: Optional list of previous messages for context
            
        Returns:
            Dictionary containing routing information including selected agent,
            confidence score, and other metadata
        """
        # Build the prompt for routing
        prompt = self._build_routing_prompt(user_message, available_agents, conversation_history)
        
        # Get response from model
        response = await self.generate_text(
            prompt=prompt,
            temperature=0.3,  # Lower temperature for more consistent routing
        )
        
        # Parse the response to extract routing information
        try:
            routing_data = json.loads(response["text"])
            return routing_data
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse routing response as JSON: {response['text']}")
            # Return a fallback routing with low confidence
            return {
                "selected_agent": "fallback",
                "confidence_score": 0.3,
                "requires_clarification": True,
                "clarification_question": "I'm not sure I understood your request. Could you please rephrase it?"
            }
    
    def _build_intent_detection_prompt(self, user_message: str, conversation_history: List[Message] = None) -> str:
        """
        Build a prompt for intent detection.
        
        Args:
            user_message: The user's message
            conversation_history: Optional conversation history for context
            
        Returns:
            Formatted prompt string
        """
        system_instruction = """
        You are an intent detection system that analyzes user messages to identify the user's primary intent,
        extract relevant entities, and determine if clarification is needed. Provide your analysis as a JSON object.
        Only respond with valid JSON and nothing else.
        """
        
        history_context = ""
        if conversation_history:
            # Format the conversation history
            history_context = "Previous conversation:\n"
            for msg in conversation_history[-5:]:  # Use last 5 messages for context
                role = "User" if msg.is_user else "Assistant"
                history_context += f"{role}: {msg.content}\n"
        
        prompt = f"""
        {system_instruction}
        
        {history_context if history_context else ""}
        
        Current user message: "{user_message}"
        
        Analyze this message to detect the primary intent, extract entities, and determine if clarification is needed.
        
        Respond with a JSON object in the following format:
        {{
            "primary_intent": "intent_category",
            "confidence": 0.95,
            "entities": {{
                "entity_name": "entity_value",
                ...
            }},
            "secondary_intents": ["intent1", "intent2"],
            "requires_clarification": false,
            "clarification_question": "Optional question if clarification is needed"
        }}
        """
        
        return prompt
    
    def _build_routing_prompt(self, user_message: str, available_agents: List[str], conversation_history: List[Message] = None) -> str:
        """
        Build a prompt for request routing.
        
        Args:
            user_message: The user's message
            available_agents: List of available agent names
            conversation_history: Optional conversation history for context
            
        Returns:
            Formatted prompt string
        """
        # Create a description of each agent's capabilities
        agent_descriptions = {
            "WeatherAgent": "Handles weather forecasts, current conditions, and weather-related advice.",
            "CalendarAgent": "Manages scheduling, reminders, appointments, and event organization.",
            "SearchAgent": "Performs web searches and information retrieval on general topics.",
            "EmailAgent": "Helps with drafting, sending, and managing emails.",
            "NavigationAgent": "Provides directions, travel times, and location-based information.",
            # Add descriptions for other agents
        }
        
        # Filter descriptions to only include available agents
        available_agent_descriptions = "\n".join([
            f"- {agent}: {agent_descriptions.get(agent, 'No description available.')}"
            for agent in available_agents
        ])
        
        history_context = ""
        if conversation_history:
            # Format the conversation history
            history_context = "Previous conversation:\n"
            for msg in conversation_history[-5:]:  # Use last 5 messages for context
                role = "User" if msg.is_user else "Assistant"
                history_context += f"{role}: {msg.content}\n"
        
        system_instruction = """
        You are a routing system for a modular AI assistant. Your job is to analyze user requests and determine
        which specialized agent should handle the request. Provide your routing decision as a JSON object.
        Only respond with valid JSON and nothing else.
        """
        
        prompt = f"""
        {system_instruction}
        
        Available specialized agents:
        {available_agent_descriptions}
        
        {history_context if history_context else ""}
        
        Current user message: "{user_message}"
        
        Analyze this message to determine which agent should handle it.
        
        Respond with a JSON object in the following format:
        {{
            "original_request": "User's original request text",
            "detected_primary_intent": "Concise description of primary intent",
            "detected_entities": {{
                "entity_type": "entity_value",
                ...
            }},
            "selected_agent": "Name of the selected agent",
            "confidence_score": 0.95,
            "secondary_agents": ["Agent1", "Agent2"],
            "requires_clarification": false,
            "clarification_question": "Optional question if clarification needed",
            "context_to_forward": "Processed context to send to the agent"
        }}
        """
        
        return prompt

    async def batch_generate(self, prompts: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Generate responses for multiple prompts in parallel.
        
        Args:
            prompts: List of prompts to process
            **kwargs: Additional parameters to pass to generate_text
            
        Returns:
            List of response dictionaries
        """
        tasks = [self.generate_text(prompt, **kwargs) for prompt in prompts]
        return await asyncio.gather(*tasks)

    async def close(self):
        """Clean up resources when done."""
        # Currently no cleanup needed for Vertex AI client
        pass