# MAIA - Modular Artificial Intelligent Assistant

MAIA is a multi-agent conversational AI system designed to handle complex user requests through specialized agents. Built with a modular architecture, MAIA can intelligently route conversations to appropriate specialized agents while maintaining context and providing seamless user experiences.

## 🌟 Features

- **Multi-Agent Architecture**: Specialized agents for different domains (weather, calendar, search, etc.)
- **Intelligent Routing**: Automatic request dispatching to the most appropriate agent
- **Context Management**: Maintains conversation history and context across interactions
- **Asynchronous Processing**: Background task processing for improved performance
- **RESTful API**: Clean API interface for integration with various frontends
- **Extensible Design**: Easy to add new specialized agents
- **Memory Management**: Persistent storage of conversation states and user preferences
- **Rate Limiting**: Built-in protection against API abuse

## 🏗️ Architecture

MAIA follows a distributed architecture with the following core components:

- **Agent Manager**: Orchestrates communication between different agents
- **Dispatcher**: Analyzes user requests and routes them to appropriate agents
- **Message Broker**: Handles inter-agent communication
- **Memory Manager**: Manages conversation state and long-term memory
- **Specialized Agents**: Domain-specific agents (Weather, Calendar, Search, etc.)

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git
- Google Gemini API key

## 🤖 Available Agents

### Search Agent
Performs web searches and provides information from various sources.

**Example queries:**
- "Find information about machine learning"
- "Search for the latest news about AI"
- "What is the capital of Australia?"

## 📊 Monitoring and Logging

MAIA includes comprehensive logging and monitoring:

- **Structured Logging**: JSON-formatted logs with different levels
- **Request Tracking**: Trace requests through the system
- **Performance Metrics**: Monitor response times and resource usage
- **Error Tracking**: Detailed error logging and reporting

Logs are stored in the `logs/` directory and can be configured in `utils/logger.py`.

### Scaling

MAIA supports horizontal scaling:

- **Message Broker**: RabbitMQ cluster for high availability

## 📋 Requirements

### Core Dependencies
- **Pydantic**: Data validation and settings management
- **RabbitMQ**: Message broker and caching
- **LangChain**: Framework for LLM applications
- **Google Generative AI**: Google Gemini API client

### External Services

- **Google Gemini API**: Primary LLM provider
- **PostgreSQL**: Primary database
- **RabbitMQ**: Message broker and cache
- **Various APIs**: Weather, Calendar, Search services
