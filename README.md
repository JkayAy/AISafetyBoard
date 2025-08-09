# AI Safety Benchmark Leaderboard

A production-ready web application for evaluating Large Language Models (LLMs) across multiple safety metrics including hallucination detection, jailbreak resistance, and bias assessment.

## 🚀 Features

### Core Functionality
- **Multi-Provider LLM Integration**: Support for OpenAI, Anthropic, Cohere, and HuggingFace models
- **Comprehensive Safety Testing**:
  - **Hallucination Detection**: Tests factual accuracy against verified ground-truth data
  - **Jailbreak Resistance**: Evaluates model responses to harmful prompt attempts
  - **Bias Detection**: Measures consistency across demographic variations
- **Interactive Leaderboard**: Sortable, searchable results with historical trends
- **Public API**: RESTful endpoints for external submissions and data retrieval
- **Admin Interface**: Secure test execution and model management

### Safety Metrics

#### 🎯 Hallucination Test
Tests model accuracy on factual questions across multiple domains:
- Geography, History, Science, Literature, Mathematics
- Exact match and fuzzy matching for answer validation
- Scoring based on percentage of correct responses

#### 🛡️ Jailbreak Resistance Test
Evaluates resistance to harmful prompt attempts:
- Multiple jailbreak techniques (roleplay, instruction override, emotional manipulation)
- Risk level classification (low, medium, high)
- Scoring based on percentage of attempts successfully blocked

#### ⚖️ Bias Detection Test
Measures fairness across demographic variations:
- Gender, race, age, disability, socioeconomic status
- Minimal pairs methodology (identical prompts with demographic changes)
- Consistency scoring for unbiased responses

## 🏗️ Architecture

