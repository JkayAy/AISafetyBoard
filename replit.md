# Overview

The AI Safety Benchmark Leaderboard is a comprehensive, production-ready web application that evaluates Large Language Models (LLMs) across multiple safety metrics. The enhanced system now includes 10 major new features:

**Core Features:**
- Multi-provider LLM testing (OpenAI, Anthropic, Cohere, HuggingFace) 
- Three comprehensive safety frameworks (hallucination, jailbreak, bias detection)
- Interactive leaderboard with sortable results and advanced filtering
- Public API for external integrations and submissions

**Enhanced Features (New):**
1. **User Authentication with OAuth** - Social media login (GitHub, Google) and secure user management
2. **Advanced Analytics Dashboard** - Performance trends, provider analysis, and real-time insights
3. **Custom Testing Framework** - User-defined test creation with templates and community sharing
4. **Notifications System** - Real-time alerts for test completions, model updates, and system events
5. **Collaboration Hub** - Content sharing, team workspaces, comments, and activity feeds
6. **Enhanced Security** - Rate limiting, input validation, security logging, and admin dashboard
7. **Comprehensive Documentation** - Getting started guides, API reference, and methodology explanations
8. **Feedback System** - Model reviews, feature requests, and community engagement
9. **Admin Panel** - User management, system monitoring, and configuration controls
10. **Mobile-Responsive UI** - Enhanced interface with modern design and accessibility features

# User Preferences

**Communication Style:** Simple, everyday language.

**Feature Priorities:** The user requested 10 specific enhancements without compromising the existing working application:
1. User Authentication with OAuth social media integration
2. Detailed Analytics Dashboard with visualizations and real-time updates  
3. Custom Testing Framework for user-defined tests
4. Model Training Capabilities (placeholder implementation)
5. Notifications System for alerts and updates
6. Enhanced Documentation and API reference
7. Collaboration Features including sharing and teamwork tools
8. Enhanced Security with rate limiting and input validation
9. Feedback System for user reviews and suggestions
10. All features integrated seamlessly into existing architecture

**Implementation Approach:** Maintain stability of core application while adding comprehensive new functionality through modular architecture.

# System Architecture

## Frontend Architecture
The application uses **Streamlit** as the primary web framework, providing a comprehensive interactive dashboard with enhanced user experience:

- **Multi-page Navigation**: Leaderboard, analytics, custom tests, collaboration hub, documentation, and admin panels
- **User Authentication Interface**: Login, registration, and OAuth integration pages
- **Enhanced UI Components**: Modern design with custom CSS, metric containers, status indicators, and responsive layouts  
- **Advanced Visualizations**: Plotly charts for performance trends, provider comparisons, and real-time analytics
- **Interactive Features**: Comments, notifications panel, activity feeds, and collaborative workspaces

## Backend Architecture
The system follows a **modular, feature-rich architecture** with enhanced capabilities:

**Core Modules:**
- **FastAPI API Layer** (`api.py`): RESTful endpoints with enhanced security and admin functions
- **Database Layer** (`database.py`): SQLite-based persistence with performance optimization
- **Model Integration** (`models.py`): Multi-provider LLM interfaces with error handling
- **Testing Framework** (`tests.py`): Comprehensive safety evaluation with extensibility

**Enhanced Modules:**
- **Authentication System** (`auth.py`): User management, OAuth integration, session handling
- **Analytics Engine** (`analytics.py`): Performance tracking, trend analysis, usage metrics
- **Security Framework** (`security.py`): Rate limiting, input validation, security logging
- **Custom Testing** (`custom_tests.py`): User-defined tests with templates and execution engine
- **Collaboration System** (`collaboration.py`): Sharing, workspaces, comments, activity feeds
- **Notifications Service** (`notifications.py`): Real-time alerts, email queuing, preference management
- **Enhanced Application** (`enhanced_app.py`): Main application with integrated features

## Data Storage Solutions
The system uses **SQLite** with an expanded database schema supporting all enhanced features:

**Core Tables:**
- `models`: Model metadata and configuration
- `test_results`: Evaluation results and performance metrics

**User & Authentication:**
- `users`: User profiles, OAuth data, preferences
- `user_sessions`: Session management and security tokens
- `notification_preferences`: User-specific notification settings

**Analytics & Tracking:**
- `performance_history`: Historical performance data for trending
- `usage_analytics`: Platform usage events and metrics
- `model_feedback`: User ratings and reviews

**Collaboration:**
- `shared_links`: Content sharing with permission controls
- `collaboration_comments`: Discussion threads on shared content
- `workspaces`: Team collaboration environments
- `workspace_members`: Team membership and roles
- `activity_feed`: Real-time activity tracking

**Custom Testing:**
- `custom_tests`: User-defined test definitions
- `custom_test_results`: Execution results for custom tests
- `test_templates`: Reusable test patterns

**Security & Notifications:**
- `security_events`: Security monitoring and logging
- `notifications`: User notification queue
- `notification_templates`: Templated notification content
- `email_queue`: Batched email delivery system

## Authentication and Authorization
The system implements a **comprehensive authentication system** with multiple layers:

**User Authentication:**
- Traditional username/password authentication with secure password hashing (bcrypt)
- OAuth integration with GitHub and Google for social media login
- Session management with secure tokens and expiration
- User roles (admin, member, viewer) with permission-based access control

**API Security:**
- API key-based authentication for programmatic access
- Rate limiting with customizable thresholds and time windows
- Input validation and sanitization to prevent injection attacks
- Security event logging and monitoring

**Session Management:**
- Secure session tokens with configurable expiration
- Session validation middleware
- Automatic cleanup of expired sessions
- Multi-device session support

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