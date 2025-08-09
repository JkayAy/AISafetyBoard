"""
AI Safety Benchmark Leaderboard - FastAPI Backend
API endpoints for external access and admin functions.
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from database import Database
from models import ModelManager
from tests import SafetyTester
import asyncio
from datetime import datetime

app = FastAPI(
    title="AI Safety Benchmark Leaderboard API",
    description="API for submitting models and retrieving benchmark results",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = Database()
model_manager = ModelManager()
safety_tester = SafetyTester()

# Admin API key
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin_key_change_me")

# Pydantic models
class ModelSubmission(BaseModel):
    """Model submission request schema."""
    name: str
    provider: str
    version: Optional[str] = None
    api_endpoint: Optional[str] = None
    description: Optional[str] = None

class TestRequest(BaseModel):
    """Test execution request schema."""
    model_id: int
    run_hallucination: bool = True
    run_jailbreak: bool = True
    run_bias: bool = True

class LeaderboardEntry(BaseModel):
    """Leaderboard entry response schema."""
    model_name: str
    provider: str
    overall_score: float
    hallucination_score: float
    jailbreak_score: float
    bias_score: float
    last_updated: datetime

# Dependency for admin authentication
async def verify_admin_key(x_admin_key: str = Header(None)):
    """Verify admin API key from header."""
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return x_admin_key

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Safety Benchmark Leaderboard API",
        "version": "1.0.0",
        "endpoints": {
            "GET /results": "Retrieve leaderboard data",
            "POST /submit": "Submit new model",
            "POST /run-tests": "Run tests (admin only)",
            "GET /models": "List all models",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        models = db.get_all_models()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "database": "connected",
            "models_count": len(models)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/results", response_model=List[LeaderboardEntry])
async def get_results(limit: Optional[int] = None, model_name: Optional[str] = None):
    """
    Retrieve leaderboard results.
    
    Args:
        limit: Maximum number of results to return
        model_name: Filter by model name (partial match)
    
    Returns:
        List of leaderboard entries with scores and metadata
    """
    try:
        results = db.get_leaderboard_data(limit=limit, model_filter=model_name)
        
        leaderboard_entries = []
        for result in results:
            entry = LeaderboardEntry(
                model_name=result['model_name'],
                provider=result['provider'],
                overall_score=result['overall_score'],
                hallucination_score=result['hallucination_score'],
                jailbreak_score=result['jailbreak_score'],
                bias_score=result['bias_score'],
                last_updated=result['last_updated']
            )
            leaderboard_entries.append(entry)
        
        return leaderboard_entries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")

@app.get("/models")
async def get_models():
    """
    Get list of all submitted models.
    
    Returns:
        List of model metadata
    """
    try:
        models = db.get_all_models()
        return models
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve models: {str(e)}")

@app.post("/submit")
async def submit_model(model: ModelSubmission):
    """
    Submit a new model for benchmarking.
    
    Args:
        model: Model submission data
    
    Returns:
        Confirmation message with model ID
    """
    try:
        # Validate provider
        valid_providers = ["openai", "anthropic", "cohere", "huggingface"]
        if model.provider not in valid_providers:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid provider. Must be one of: {valid_providers}"
            )
        
        # Check if model already exists
        existing_models = db.get_all_models()
        for existing in existing_models:
            if existing['name'] == model.name and existing['provider'] == model.provider:
                raise HTTPException(
                    status_code=409, 
                    detail="Model with this name and provider already exists"
                )
        
        # Add model to database
        model_id = db.add_model(
            name=model.name,
            provider=model.provider,
            version=model.version,
            api_endpoint=model.api_endpoint,
            description=model.description
        )
        
        return {
            "message": "Model submitted successfully",
            "model_id": model_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit model: {str(e)}")

@app.post("/run-tests")
async def run_tests(test_request: TestRequest, admin_key: str = Depends(verify_admin_key)):
    """
    Run safety tests on a model (admin only).
    
    Args:
        test_request: Test configuration
        admin_key: Admin authentication (from header)
    
    Returns:
        Test results and scores
    """
    try:
        # Get model information
        models = db.get_all_models()
        model_info = next((m for m in models if m['id'] == test_request.model_id), None)
        
        if not model_info:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Initialize model client
        model_client = model_manager.get_model_client(
            provider=model_info['provider'],
            model_name=model_info['name'],
            api_endpoint=model_info.get('api_endpoint')
        )
        
        if not model_client:
            raise HTTPException(
                status_code=400, 
                detail=f"Could not initialize client for provider: {model_info['provider']}"
            )
        
        # Run tests
        results = {}
        example_outputs = {}
        
        if test_request.run_hallucination:
            hallucination_score, examples = await asyncio.to_thread(
                safety_tester.test_hallucination, model_client
            )
            results['hallucination_score'] = hallucination_score
            example_outputs['hallucination'] = examples
        
        if test_request.run_jailbreak:
            jailbreak_score, examples = await asyncio.to_thread(
                safety_tester.test_jailbreak_resistance, model_client
            )
            results['jailbreak_score'] = jailbreak_score
            example_outputs['jailbreak'] = examples
        
        if test_request.run_bias:
            bias_score, examples = await asyncio.to_thread(
                safety_tester.test_bias_detection, model_client
            )
            results['bias_score'] = bias_score
            example_outputs['bias'] = examples
        
        # Calculate overall score
        scores = [score for score in results.values() if score is not None]
        overall_score = sum(scores) / len(scores) if scores else 0
        
        # Store results in database
        result_id = db.add_test_result(
            model_id=test_request.model_id,
            overall_score=overall_score,
            hallucination_score=results.get('hallucination_score'),
            jailbreak_score=results.get('jailbreak_score'),
            bias_score=results.get('bias_score'),
            example_outputs=example_outputs
        )
        
        return {
            "message": "Tests completed successfully",
            "result_id": result_id,
            "scores": {
                "overall_score": overall_score,
                **results
            },
            "example_outputs": example_outputs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run tests: {str(e)}")

@app.get("/model/{model_id}/results")
async def get_model_results(model_id: int):
    """
    Get historical test results for a specific model.
    
    Args:
        model_id: ID of the model
    
    Returns:
        List of historical test results
    """
    try:
        results = db.get_model_results(model_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve model results: {str(e)}")

@app.delete("/model/{model_id}")
async def delete_model(model_id: int, admin_key: str = Depends(verify_admin_key)):
    """
    Delete a model and all its results (admin only).
    
    Args:
        model_id: ID of the model to delete
        admin_key: Admin authentication
    
    Returns:
        Confirmation message
    """
    try:
        # Check if model exists
        models = db.get_all_models()
        model_info = next((m for m in models if m['id'] == model_id), None)
        
        if not model_info:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Delete model and associated results
        db.delete_model(model_id)
        
        return {
            "message": f"Model '{model_info['name']}' and all associated results deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return HTTPException(status_code=404, detail="Endpoint not found")

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
