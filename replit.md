# Overview

The AI Safety Benchmark Leaderboard is a production-ready web application that evaluates Large Language Models (LLMs) across multiple safety metrics. The system tests models from various providers (OpenAI, Anthropic, Cohere, HuggingFace) for hallucination detection, jailbreak resistance, and bias assessment. It features an interactive leaderboard with sortable results, a public API for external submissions, and an admin interface for secure test execution.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
The application uses **Streamlit** as the primary web framework, providing an interactive dashboard with multiple pages including leaderboard views, model details, submission forms, and API documentation. The frontend is designed with a sidebar navigation system and utilizes Plotly for data visualization and charting.

## Backend Architecture
The system follows a **modular FastAPI architecture** with clear separation of concerns:

- **FastAPI API Layer** (`api.py`): RESTful endpoints for external access and admin functions with CORS middleware support
- **Database Layer** (`database.py`): SQLite-based data persistence with contextual connection management
- **Model Integration Layer** (`models.py`): Unified interface for multiple LLM providers using abstract base classes
- **Testing Framework** (`tests.py`): Comprehensive safety evaluation system with three core metrics
- **Utility Layer** (`utils.py`): Shared helper functions for formatting, validation, and common operations

## Data Storage Solutions
The system uses **SQLite** as the primary database with two main tables:
- `models` table: Stores model metadata (name, provider, version, API endpoints, descriptions)
- `test_results` table: Stores evaluation results with overall scores and individual metric scores

This design choice provides simplicity for deployment while maintaining relational data integrity.

## Authentication and Authorization
The system implements **API key-based authentication** for admin functions, with environment variable configuration for secure credential management. Different access levels are provided for public API access versus administrative operations.

## Testing and Evaluation Framework
The safety testing system employs three distinct methodologies:

1. **Hallucination Detection**: Uses predefined factual questions with verified ground-truth answers, employing both exact match and fuzzy matching algorithms
2. **Jailbreak Resistance**: Tests against known harmful prompt techniques with risk level classification
3. **Bias Detection**: Implements minimal pairs methodology with demographic variations to measure response consistency

## Model Integration Strategy
The system uses a **provider-agnostic approach** with abstract base classes, allowing seamless integration of multiple LLM providers through unified interfaces. Each provider implementation handles authentication, request formatting, and response parsing specific to that API.

# External Dependencies

## LLM Provider APIs
- **OpenAI API**: GPT model integration with official Python client
- **Anthropic API**: Claude model integration with official Python client  
- **Cohere API**: Cohere model integration via REST API
- **HuggingFace Inference API**: Open-source model integration via HTTP requests

## Web Framework and UI
- **Streamlit**: Primary web application framework for interactive dashboard
- **FastAPI**: REST API framework with automatic OpenAPI documentation
- **Plotly**: Data visualization and interactive charting library

## Database and Storage
- **SQLite**: Embedded relational database for data persistence
- **JSON**: Configuration and test data storage format

## Development and Deployment
- **Replit**: Target hosting platform with environment variable support
- **Python Standard Library**: Core functionality for file operations, datetime handling, and data processing

## Authentication and Security
- **Environment Variables**: Secure API key and configuration management
- **CORS Middleware**: Cross-origin request handling for web API access

## Testing and Validation
- **Regular Expressions**: Pattern matching for response validation
- **Random Sampling**: Statistical sampling for test dataset selection
- **Fuzzy Matching**: Approximate string matching for answer validation