import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import pytest

# Assumiamo che questi siano i percorsi corretti ai tuoi moduli
from core.dispatcher import Dispatcher
from models.message import Message

from core.message_broker2 import MessageBroker


class TestDispatcher(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures for each test."""
        # Mock dependencies

        
        # Create instance of Dispatcher with mocked dependencies
        self.dispatcher = Dispatcher()
        
        message_broker_config = {
            'host': 'localhost',
            'port': 5672,
            'username': 'admin',
            'password': 'password',
            'virtual_host': '/'
        }
        self._message_broker = MessageBroker(message_broker_config)
        
        # Set up standard registered agents
        '''self.dispatcher.registered_agents = {
            "WeatherAgent": {
                "capabilities": ["weather_forecast", "weather_current", "weather_historical"],
                "keywords": ["weather", "temperature", "rain", "forecast", "climate"],
                "confidence_threshold": 0.7
            },
            "CalendarAgent": {
                "capabilities": ["calendar_create", "calendar_read", "calendar_update", "calendar_delete"],
                "keywords": ["schedule", "meeting", "appointment", "calendar", "event", "remind"],
                "confidence_threshold": 0.7
            },
            "SearchAgent": {
                "capabilities": ["web_search", "information_retrieval"],
                "keywords": ["search", "find", "look up", "information", "details"],
                "confidence_threshold": 0.6
            }
        }
'''
    def test_single_intent_clear_weather(self):
        """Test clear weather intent routing."""
        # Create test message
        message = Message(
            content="What's the weather like in Rome today?",
            user_id="test_user_1",
            conversation_id="test_conv_1"
        )
        


        
        # Test dispatcher processing
        result = self.dispatcher.analyze_request(message)
        
        # Assertions
        self.assertEqual(result["selected_agent"], "WeatherAgent")
        self.assertGreater(result["confidence_score"], 0.8)
        self.assertFalse(result["requires_clarification"])
        self.assertEqual(result["detected_primary_intent"], "weather_current")
        self.assertIn("location", result["detected_entities"])
        self.assertEqual(result["detected_entities"]["location"], "Rome")
        

        
        # Verify memory was updated


    def test_single_intent_clear_calendar(self):
        """Test clear calendar intent routing."""
        # Create test message
        message = Message(
            content="Schedule a team meeting for tomorrow at 3 PM",
            user_id="test_user_1",
            conversation_id="test_conv_1"
        )
        


        
        # Test dispatcher processing
        result = self.dispatcher.process_request(message)
        
        # Assertions
        self.assertEqual(result["selected_agent"], "CalendarAgent")
        self.assertGreater(result["confidence_score"], 0.8)
        self.assertFalse(result["requires_clarification"])
        self.assertEqual(result["detected_primary_intent"], "calendar_create")
        self.assertIn("event_type", result["detected_entities"])
        self.assertEqual(result["detected_entities"]["event_type"], "meeting")
        self.assertIn("time", result["detected_entities"])
        


    def test_ambiguous_request(self):
        """Test handling of ambiguous requests."""
        # Create test message with ambiguity
        message = Message(
            content="Remind me about the meeting",
            user_id="test_user_1",
            conversation_id="test_conv_1"
        )
        


        
        # Test dispatcher processing
        result = self.dispatcher.process_request(message)
        
        # Assertions
        self.assertEqual(result["selected_agent"], "CalendarAgent")  # Most likely agent
        self.assertLess(result["confidence_score"], 0.7)  # Low confidence
        self.assertTrue(result["requires_clarification"])
        self.assertIsNotNone(result["clarification_question"])
        
        # Verify agent interaction was NOT made due to low confidence

    def test_multi_intent_request(self):
        """Test handling multi-intent requests."""
        # Create test message with multiple intents
        message = Message(
            content="What's the weather in Paris tomorrow and schedule a meeting with marketing at 2 PM",
            user_id="test_user_1",
            conversation_id="test_conv_1"
        )
        


        
        # Test dispatcher processing
        result = self.dispatcher.process_request(message)
        
        # Assertions
        self.assertEqual(result["selected_agent"], "WeatherAgent")  # Primary intent
        self.assertIn("CalendarAgent", result["secondary_agents"])  # Secondary intent
        self.assertFalse(result["requires_clarification"])
        
        # Verify multiple agents were called

    def test_context_dependent_request(self):
        """Test handling of context-dependent requests."""
        # Setup previous context with weather discussion
        previous_context = {
            "messages": [
                {"role": "user", "content": "What's the weather like in Tokyo?"},
                {"role": "assistant", "content": "It's currently sunny and 25°C in Tokyo."}
            ],
            "last_agent": "WeatherAgent",
            "entities": {"location": "Tokyo"}
        }
        

        
        # Create a follow-up message with implicit reference
        message = Message(
            content="How about tomorrow?",
            user_id="test_user_1",
            conversation_id="test_conv_1"
        )
        
        # Test dispatcher processing
        result = self.dispatcher.process_request(message)
        
        # Assertions
        self.assertEqual(result["selected_agent"], "WeatherAgent")  # Same as context
        self.assertGreater(result["confidence_score"], 0.7)
        self.assertFalse(result["requires_clarification"])
        
        # Verify context was incorporated
        self.assertIn("location", result["detected_entities"])
        self.assertEqual(result["detected_entities"]["location"], "Tokyo")  # Inherited from context
        
        # Verify agent was called

    def test_unknown_intent(self):
        """Test handling of unknown/unsupported intents."""
        # Create message with intent not matching any agent
        message = Message(
            content="Can you compose a symphony in A minor?",
            user_id="test_user_1",
            conversation_id="test_conv_1"
        )
        

        
        # Test dispatcher processing
        result = self.dispatcher.process_request(message)
        
        # Assertions
        self.assertEqual(result["selected_agent"], "SearchAgent")  # Fallback to search
        self.assertLess(result["confidence_score"], 0.7)  # Low confidence expected
        self.assertTrue(result["requires_clarification"]) 
        
        # Verify agent interaction behavior



    def test_switching_context(self):
        """Test handling of context switching."""
        # Setup previous context with calendar discussion
        previous_context = {
            "messages": [
                {"role": "user", "content": "Schedule a team meeting for Friday"},
                {"role": "assistant", "content": "I've scheduled a team meeting for Friday at 10 AM."}
            ],
            "last_agent": "CalendarAgent",
            "entities": {"event_type": "meeting", "day": "Friday"}
        }
        

        
        # Create a new message with different context
        message = Message(
            content="What's the weather like in Berlin?",
            user_id="test_user_1",
            conversation_id="test_conv_1"
        )
        
        # Test dispatcher processing
        result = self.dispatcher.process_request(message)
        
        # Assertions
        self.assertEqual(result["selected_agent"], "WeatherAgent")  # New context agent
        self.assertGreater(result["confidence_score"], 0.8)  # High confidence for clear intent
        self.assertFalse(result["requires_clarification"])
        
        # Verify context switch was recognized
        self.assertNotEqual(result["selected_agent"], previous_context["last_agent"])
        
        # Verify agent was called with new context


    def test_clarification_response_handling(self):
        """Test handling of responses to clarification questions."""
        # Setup previous context with ambiguous request and clarification
        previous_context = {
            "messages": [
                {"role": "user", "content": "Remind me about the meeting"},
                {"role": "assistant", "content": "I'd be happy to remind you about your meeting. Could you specify which meeting you're referring to or when it's scheduled?"}
            ],
            "pending_clarification": {
                "original_intent": "calendar_read",
                "potential_agents": ["CalendarAgent"],
                "missing_entities": ["specific_meeting", "time"]
            }
        }
        

        
        # Create clarification response
        message = Message(
            content="The marketing strategy meeting tomorrow at 2 PM",
            user_id="test_user_1",
            conversation_id="test_conv_1"
        )
        
        # Test dispatcher processing
        result = self.dispatcher.process_request(message)
        
        # Assertions
        self.assertEqual(result["selected_agent"], "CalendarAgent")
        self.assertGreater(result["confidence_score"], 0.8)  # High confidence with clarification
        self.assertFalse(result["requires_clarification"])
        
        # Verify entities were merged correctly
        self.assertIn("event_type", result["detected_entities"])
        self.assertEqual(result["detected_entities"]["event_type"], "marketing strategy meeting")
        self.assertIn("time", result["detected_entities"])
        
        # Verify agent was called with complete information



@pytest.mark.parametrize("request_text,expected_agent,requires_clarification", [
    # Weather requests
    ("What's the weather like today?", "WeatherAgent", False),
    ("Will it rain tomorrow in New York?", "WeatherAgent", False),
    ("Temperature in Tokyo next week", "WeatherAgent", False),
    ("Is it going to be sunny this weekend?", "WeatherAgent", False),
    
    # Calendar requests  
    ("Schedule a meeting with the team tomorrow", "CalendarAgent", False),
    ("Move my 2 PM appointment to 4 PM", "CalendarAgent", False),
    ("What's on my calendar for next week?", "CalendarAgent", False),
    ("Cancel my dentist appointment", "CalendarAgent", False),
    
    # Search requests
    ("Find information about quantum computing", "SearchAgent", False),
    ("Look up the population of Canada", "SearchAgent", False),
    
    # Ambiguous requests
    ("The meeting", "CalendarAgent", True),
    ("Tomorrow", None, True),
    ("Check it for me", None, True),
    
    # Complex/multi-intent requests  
    ("What's the weather tomorrow and schedule a team lunch", "WeatherAgent", False),
    ("Find information about Paris and check if it will rain there next week", "SearchAgent", False),
    
    # Context switching examples
    ("What time is my meeting tomorrow and what's the weather going to be like?", "CalendarAgent", False),
    ("After my meeting, find me a good restaurant nearby", "CalendarAgent", False),
])
def test_various_requests(request_text, expected_agent, requires_clarification):
    """Parametrized test for various request types."""
    # Setup mocks


    
    # Create dispatcher

    
    # Setup standard agents
    dispatcher.registered_agents = {
        "WeatherAgent": {
            "capabilities": ["weather_forecast", "weather_current", "weather_historical"],
            "keywords": ["weather", "temperature", "rain", "forecast", "climate"],
            "confidence_threshold": 0.7
        },
        "CalendarAgent": {
            "capabilities": ["calendar_create", "calendar_read", "calendar_update", "calendar_delete"],
            "keywords": ["schedule", "meeting", "appointment", "calendar", "event", "remind"],
            "confidence_threshold": 0.7
        },
        "SearchAgent": {
            "capabilities": ["web_search", "information_retrieval"],
            "keywords": ["search", "find", "look up", "information", "details"],
            "confidence_threshold": 0.6
        }
    }
    


    
    # Create message
    message = Message(
        content=request_text,
        user_id="test_user_1",
        conversation_id="test_conv_1"
    )
    
    # Process request
    result = dispatcher.process_request(message)
    
    # Assertions
    if not requires_clarification:
        assert result["selected_agent"] == expected_agent
        assert result["requires_clarification"] == requires_clarification
    else:
        assert result["requires_clarification"] == requires_clarification


# Integration tests for the full dispatcher workflow
class TestDispatcherIntegration:
    @pytest.fixture
    def setup_dependencies(self):
        """Setup integration test dependencies."""
        # Create real dependencies or more sophisticated mocks


        


        
        # Configure the agent manager to return realistic responses

        
        # Configure dispatcher with dependencies

        
        # Register agents
        dispatcher.register_agent("WeatherAgent", {
            "capabilities": ["weather_forecast", "weather_current", "weather_historical"],
            "keywords": ["weather", "temperature", "rain", "forecast", "climate"],
            "confidence_threshold": 0.7
        })
        
        dispatcher.register_agent("CalendarAgent", {
            "capabilities": ["calendar_create", "calendar_read", "calendar_update", "calendar_delete"],
            "keywords": ["schedule", "meeting", "appointment", "calendar", "event", "remind"],
            "confidence_threshold": 0.7
        })
        
        dispatcher.register_agent("SearchAgent", {
            "capabilities": ["web_search", "information_retrieval"],
            "keywords": ["search", "find", "look up", "information", "details"],
            "confidence_threshold": 0.6
        })
        

    
    def test_full_request_workflow(self, setup_dependencies):
        """Test the full request workflow from receipt to agent routing."""

        
        # Create a test message
        message = Message(
            content="What's the weather forecast for Rome tomorrow?",
            user_id="test_user_integration",
            conversation_id="test_conv_integration"
        )
        
        # Process the request
        result = dispatcher.process_request(message)
        
        # Verify the full workflow
        assert result["selected_agent"] == "WeatherAgent"
        assert result["detected_primary_intent"] == "weather_forecast"
        assert result["detected_entities"]["location"] == "Rome"
        assert result["detected_entities"]["time"] == "tomorrow"
        
        # Verify memory was updated

        
        # Verify agent was called

        
        # Verify the response was processed

    
    def test_conversation_continuity(self, setup_dependencies):
        """Test that conversation context is maintained correctly."""

        

        
        # Create follow-up message
        message = Message(
            content="How about tomorrow?",
            user_id="test_user_integration",
            conversation_id="test_conv_integration"
        )
        
        # Process the request
        result = dispatcher.process_request(message)
        
        # Verify context continuity
        assert result["selected_agent"] == "WeatherAgent"
        assert "location" in result["detected_entities"]
        assert result["detected_entities"]["location"] == "Paris"  # From previous context
        assert "time" in result["detected_entities"]
        assert result["detected_entities"]["time"] == "tomorrow"  # From current request


if __name__ == "__main__":
    unittest.main()