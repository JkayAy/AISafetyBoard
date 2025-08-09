"""
AI Safety Benchmark Leaderboard - Database Management
SQLite database operations for storing models, results, and metadata.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

class Database:
    """Database manager for the AI Safety Benchmark Leaderboard."""
    
    def __init__(self, db_path: str = "leaderboard.db"):
        """
        Initialize database connection and create tables.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Models table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    version TEXT,
                    api_endpoint TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, provider)
                )
            """)
            
            # Test results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id INTEGER NOT NULL,
                    overall_score REAL,
                    hallucination_score REAL,
                    jailbreak_score REAL,
                    bias_score REAL,
                    example_outputs TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE CASCADE
                )
            """)
            
            # Create indices for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_models_provider ON models(provider)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_models_name ON models(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_model_id ON test_results(model_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_created_at ON test_results(created_at)")
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def add_model(self, name: str, provider: str, version: Optional[str] = None, 
                  api_endpoint: Optional[str] = None, description: Optional[str] = None) -> int:
        """
        Add a new model to the database.
        
        Args:
            name: Model name
            provider: API provider (openai, anthropic, cohere, huggingface)
            version: Model version
            api_endpoint: Custom API endpoint
            description: Model description
        
        Returns:
            int: Model ID
        
        Raises:
            ValueError: If model already exists
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO models (name, provider, version, api_endpoint, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, provider, version, api_endpoint, description))
                
                conn.commit()
                return cursor.lastrowid or 0
                
            except sqlite3.IntegrityError:
                raise ValueError(f"Model '{name}' with provider '{provider}' already exists")
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """
        Get all models from the database.
        
        Returns:
            List of model dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, provider, version, api_endpoint, description, created_at
                FROM models
                ORDER BY created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_model_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific model by ID.
        
        Args:
            model_id: Model ID
        
        Returns:
            Model dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, provider, version, api_endpoint, description, created_at
                FROM models
                WHERE id = ?
            """, (model_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def delete_model(self, model_id: int) -> bool:
        """
        Delete a model and all its associated results.
        
        Args:
            model_id: Model ID to delete
        
        Returns:
            True if model was deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete model (cascade will handle test_results)
            cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
            conn.commit()
            
            return cursor.rowcount > 0
    
    def add_test_result(self, model_id: int, overall_score: Optional[float] = None,
                       hallucination_score: Optional[float] = None,
                       jailbreak_score: Optional[float] = None,
                       bias_score: Optional[float] = None,
                       example_outputs: Optional[Dict[str, Any]] = None) -> int:
        """
        Add test results for a model.
        
        Args:
            model_id: Model ID
            overall_score: Overall safety score
            hallucination_score: Hallucination test score
            jailbreak_score: Jailbreak resistance score
            bias_score: Bias detection score
            example_outputs: Example outputs from tests
        
        Returns:
            Test result ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Serialize example outputs to JSON
            outputs_json = json.dumps(example_outputs) if example_outputs else None
            
            cursor.execute("""
                INSERT INTO test_results 
                (model_id, overall_score, hallucination_score, jailbreak_score, 
                 bias_score, example_outputs)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (model_id, overall_score, hallucination_score, jailbreak_score,
                  bias_score, outputs_json))
            
            conn.commit()
            return cursor.lastrowid or 0
    
    def get_leaderboard_data(self, limit: Optional[int] = None, 
                           model_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get leaderboard data with latest results for each model.
        
        Args:
            limit: Maximum number of results to return
            model_filter: Filter by model name (partial match)
        
        Returns:
            List of leaderboard entries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Query to get latest results for each model
            query = """
                SELECT DISTINCT
                    m.id as model_id,
                    m.name as model_name,
                    m.provider,
                    m.version,
                    r.overall_score,
                    r.hallucination_score,
                    r.jailbreak_score,
                    r.bias_score,
                    r.created_at as last_updated,
                    r.example_outputs
                FROM models m
                LEFT JOIN test_results r ON m.id = r.model_id
                WHERE r.id = (
                    SELECT id FROM test_results r2 
                    WHERE r2.model_id = m.id 
                    ORDER BY r2.created_at DESC 
                    LIMIT 1
                )
            """
            
            params = []
            
            # Add model name filter
            if model_filter:
                query += " AND m.name LIKE ?"
                params.append(f"%{model_filter}%")
            
            # Order by overall score (highest first)
            query += " ORDER BY r.overall_score DESC"
            
            # Add limit
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_model_results(self, model_id: int) -> List[Dict[str, Any]]:
        """
        Get all test results for a specific model.
        
        Args:
            model_id: Model ID
        
        Returns:
            List of test results ordered by date
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, overall_score, hallucination_score, jailbreak_score,
                       bias_score, example_outputs, created_at
                FROM test_results
                WHERE model_id = ?
                ORDER BY created_at DESC
            """, (model_id,))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # Parse example outputs JSON
                if result['example_outputs']:
                    try:
                        result['example_outputs'] = json.loads(result['example_outputs'])
                    except json.JSONDecodeError:
                        result['example_outputs'] = None
                results.append(result)
            
            return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count models
            cursor.execute("SELECT COUNT(*) FROM models")
            total_models = cursor.fetchone()[0]
            
            # Count test results
            cursor.execute("SELECT COUNT(*) FROM test_results")
            total_results = cursor.fetchone()[0]
            
            # Get provider distribution
            cursor.execute("""
                SELECT provider, COUNT(*) as count
                FROM models
                GROUP BY provider
                ORDER BY count DESC
            """)
            provider_distribution = [dict(row) for row in cursor.fetchall()]
            
            # Get average scores
            cursor.execute("""
                SELECT 
                    AVG(overall_score) as avg_overall,
                    AVG(hallucination_score) as avg_hallucination,
                    AVG(jailbreak_score) as avg_jailbreak,
                    AVG(bias_score) as avg_bias
                FROM test_results
                WHERE overall_score IS NOT NULL
            """)
            avg_scores = dict(cursor.fetchone()) if cursor.fetchone() else {}
            
            return {
                "total_models": total_models,
                "total_results": total_results,
                "provider_distribution": provider_distribution,
                "average_scores": avg_scores
            }
    
    def cleanup_old_results(self, days: int = 30) -> int:
        """
        Clean up test results older than specified days.
        
        Args:
            days: Number of days to keep results
        
        Returns:
            Number of deleted records
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM test_results
                WHERE created_at < datetime('now', '-{} days')
            """.format(days))
            
            conn.commit()
            return cursor.rowcount
