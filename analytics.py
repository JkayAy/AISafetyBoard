"""
Advanced analytics dashboard for AI Safety Benchmark Leaderboard
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sqlite3
from database import DatabaseManager
import json

class AnalyticsManager:
    """Handles analytics data processing and visualization"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._initialize_analytics_tables()
    
    def _initialize_analytics_tables(self):
        """Initialize analytics-specific tables"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Model performance history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                overall_score REAL,
                hallucination_score REAL,
                jailbreak_score REAL,
                bias_score REAL,
                test_version TEXT,
                FOREIGN KEY (model_id) REFERENCES models (id)
            )
        """)
        
        # Usage analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id INTEGER,
                model_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (model_id) REFERENCES models (id)
            )
        """)
        
        # Model ratings and feedback
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                user_id INTEGER,
                rating INTEGER CHECK (rating BETWEEN 1 AND 5),
                feedback_text TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_performance_history(self, model_id: int, scores: Dict[str, float], 
                                 test_version: str = "1.0"):
        """Record model performance for historical tracking"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO performance_history 
            (model_id, overall_score, hallucination_score, jailbreak_score, 
             bias_score, test_version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (model_id, scores.get('overall_score'), scores.get('hallucination_score'),
              scores.get('jailbreak_score'), scores.get('bias_score'), test_version))
        
        conn.commit()
        conn.close()
    
    def log_usage_event(self, event_type: str, user_id: Optional[int] = None,
                       model_id: Optional[int] = None, metadata: Dict = None):
        """Log usage analytics event"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute("""
            INSERT INTO usage_analytics (event_type, user_id, model_id, metadata)
            VALUES (?, ?, ?, ?)
        """, (event_type, user_id, model_id, metadata_json))
        
        conn.commit()
        conn.close()
    
    def add_model_feedback(self, model_id: int, user_id: int, rating: int,
                          feedback_text: str, category: str = "general"):
        """Add user feedback for a model"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO model_feedback (model_id, user_id, rating, feedback_text, category)
            VALUES (?, ?, ?, ?, ?)
        """, (model_id, user_id, rating, feedback_text, category))
        
        conn.commit()
        conn.close()
    
    def get_performance_trends(self, days: int = 30) -> pd.DataFrame:
        """Get performance trends over time"""
        conn = sqlite3.connect(self.db.db_path)
        
        query = """
            SELECT 
                m.name as model_name,
                m.provider,
                ph.test_date,
                ph.overall_score,
                ph.hallucination_score,
                ph.jailbreak_score,
                ph.bias_score
            FROM performance_history ph
            JOIN models m ON ph.model_id = m.id
            WHERE ph.test_date >= datetime('now', '-{} days')
            ORDER BY ph.test_date DESC
        """.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['test_date'] = pd.to_datetime(df['test_date'])
        
        return df
    
    def get_provider_statistics(self) -> pd.DataFrame:
        """Get statistics by provider"""
        conn = sqlite3.connect(self.db.db_path)
        
        query = """
            SELECT 
                m.provider,
                COUNT(*) as model_count,
                AVG(tr.overall_score) as avg_overall_score,
                AVG(tr.hallucination_score) as avg_hallucination_score,
                AVG(tr.jailbreak_score) as avg_jailbreak_score,
                AVG(tr.bias_score) as avg_bias_score,
                MAX(tr.overall_score) as best_overall_score
            FROM models m
            LEFT JOIN test_results tr ON m.id = tr.model_id
            GROUP BY m.provider
            ORDER BY avg_overall_score DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_usage_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get usage analytics for the specified period"""
        conn = sqlite3.connect(self.db.db_path)
        
        # Total events
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM usage_analytics 
            WHERE timestamp >= datetime('now', '-{} days')
        """.format(days))
        total_events = cursor.fetchone()[0]
        
        # Events by type
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM usage_analytics 
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY event_type
            ORDER BY count DESC
        """.format(days))
        events_by_type = dict(cursor.fetchall())
        
        # Daily activity
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM usage_analytics 
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """.format(days))
        daily_activity = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_events": total_events,
            "events_by_type": events_by_type,
            "daily_activity": daily_activity
        }
    
    def get_model_feedback_summary(self, model_id: Optional[int] = None) -> Dict[str, Any]:
        """Get feedback summary for models"""
        conn = sqlite3.connect(self.db.db_path)
        
        where_clause = f"WHERE mf.model_id = {model_id}" if model_id else ""
        
        query = f"""
            SELECT 
                m.name as model_name,
                m.provider,
                COUNT(*) as feedback_count,
                AVG(mf.rating) as avg_rating,
                COUNT(CASE WHEN mf.rating >= 4 THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN mf.rating <= 2 THEN 1 END) as negative_feedback
            FROM model_feedback mf
            JOIN models m ON mf.model_id = m.id
            {where_clause}
            GROUP BY m.id, m.name, m.provider
            ORDER BY avg_rating DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df.to_dict('records') if not df.empty else []

def render_analytics_dashboard():
    """Render the main analytics dashboard"""
    st.title("🔍 Analytics Dashboard")
    
    # Initialize analytics manager
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    
    analytics = AnalyticsManager(st.session_state.db_manager)
    
    # Sidebar filters
    with st.sidebar:
        st.subheader("Filters")
        time_period = st.selectbox(
            "Time Period",
            options=[7, 14, 30, 60, 90],
            format_func=lambda x: f"Last {x} days",
            index=2
        )
        
        provider_filter = st.multiselect(
            "Filter by Provider",
            options=["openai", "anthropic", "cohere", "huggingface"],
            default=[]
        )
    
    # Main dashboard tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Performance Trends", 
        "🏢 Provider Analysis", 
        "📈 Usage Analytics",
        "💬 User Feedback"
    ])
    
    with tab1:
        render_performance_trends(analytics, time_period, provider_filter)
    
    with tab2:
        render_provider_analysis(analytics)
    
    with tab3:
        render_usage_analytics(analytics, time_period)
    
    with tab4:
        render_feedback_analysis(analytics)

def render_performance_trends(analytics: AnalyticsManager, days: int, providers: List[str]):
    """Render performance trends visualizations"""
    st.subheader("Model Performance Over Time")
    
    # Get trend data
    df = analytics.get_performance_trends(days)
    
    if df.empty:
        st.info("No performance data available for the selected period.")
        return
    
    # Filter by provider if specified
    if providers:
        df = df[df['provider'].isin(providers)]
    
    # Overall score trends
    st.write("### Overall Score Trends")
    if not df.empty:
        fig = px.line(
            df, 
            x='test_date', 
            y='overall_score',
            color='model_name',
            title="Overall Safety Scores Over Time",
            labels={'test_date': 'Date', 'overall_score': 'Overall Score'},
            hover_data=['provider']
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Individual metrics comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Hallucination Detection")
        if not df.empty:
            fig = px.box(
                df,
                x='provider',
                y='hallucination_score',
                color='provider',
                title="Hallucination Scores by Provider"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.write("### Jailbreak Resistance")
        if not df.empty:
            fig = px.box(
                df,
                x='provider',
                y='jailbreak_score',
                color='provider',
                title="Jailbreak Resistance by Provider"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    # Performance heatmap
    st.write("### Performance Correlation Matrix")
    if not df.empty and len(df) > 1:
        score_cols = ['overall_score', 'hallucination_score', 'jailbreak_score', 'bias_score']
        corr_matrix = df[score_cols].corr()
        
        fig = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            title="Score Correlations",
            color_continuous_scale="RdBu"
        )
        st.plotly_chart(fig, use_container_width=True)

def render_provider_analysis(analytics: AnalyticsManager):
    """Render provider comparison analysis"""
    st.subheader("Provider Performance Analysis")
    
    provider_stats = analytics.get_provider_statistics()
    
    if provider_stats.empty:
        st.info("No provider data available.")
        return
    
    # Provider overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Providers", len(provider_stats))
    
    with col2:
        total_models = int(provider_stats['model_count'].sum())
        st.metric("Total Models", total_models)
    
    with col3:
        avg_score = provider_stats['avg_overall_score'].mean()
        st.metric("Average Score", f"{avg_score:.1f}" if not pd.isna(avg_score) else "N/A")
    
    with col4:
        best_score = provider_stats['best_overall_score'].max()
        st.metric("Best Score", f"{best_score:.1f}" if not pd.isna(best_score) else "N/A")
    
    # Provider comparison chart
    st.write("### Provider Performance Comparison")
    
    fig = go.Figure()
    
    # Add bars for each metric
    metrics = [
        ('avg_overall_score', 'Overall Score'),
        ('avg_hallucination_score', 'Hallucination'),
        ('avg_jailbreak_score', 'Jailbreak'),
        ('avg_bias_score', 'Bias')
    ]
    
    for i, (metric, name) in enumerate(metrics):
        fig.add_trace(go.Bar(
            name=name,
            x=provider_stats['provider'],
            y=provider_stats[metric],
            yaxis=f'y{i+1}' if i > 0 else 'y',
            offsetgroup=i
        ))
    
    fig.update_layout(
        title="Average Scores by Provider",
        xaxis_title="Provider",
        yaxis_title="Score",
        barmode='group',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Provider details table
    st.write("### Provider Statistics")
    display_df = provider_stats.copy()
    
    # Round numerical columns
    numeric_cols = ['avg_overall_score', 'avg_hallucination_score', 
                   'avg_jailbreak_score', 'avg_bias_score', 'best_overall_score']
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(2)
    
    st.dataframe(display_df, use_container_width=True)

def render_usage_analytics(analytics: AnalyticsManager, days: int):
    """Render usage analytics"""
    st.subheader("Usage Analytics")
    
    usage_data = analytics.get_usage_analytics(days)
    
    # Usage overview metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Events", usage_data["total_events"])
    
    with col2:
        daily_avg = usage_data["total_events"] / days if days > 0 else 0
        st.metric("Daily Average", f"{daily_avg:.1f}")
    
    with col3:
        event_types = len(usage_data["events_by_type"])
        st.metric("Event Types", event_types)
    
    # Event distribution
    if usage_data["events_by_type"]:
        st.write("### Event Distribution")
        events_df = pd.DataFrame(
            list(usage_data["events_by_type"].items()),
            columns=['Event Type', 'Count']
        )
        
        fig = px.pie(
            events_df,
            values='Count',
            names='Event Type',
            title="Distribution of Events"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Daily activity
    if usage_data["daily_activity"]:
        st.write("### Daily Activity")
        activity_df = pd.DataFrame(
            usage_data["daily_activity"],
            columns=['Date', 'Events']
        )
        activity_df['Date'] = pd.to_datetime(activity_df['Date'])
        
        fig = px.line(
            activity_df,
            x='Date',
            y='Events',
            title="Daily Event Count",
            markers=True
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

def render_feedback_analysis(analytics: AnalyticsManager):
    """Render user feedback analysis"""
    st.subheader("User Feedback Analysis")
    
    feedback_data = analytics.get_model_feedback_summary()
    
    if not feedback_data:
        st.info("No feedback data available.")
        return
    
    feedback_df = pd.DataFrame(feedback_data)
    
    # Feedback overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_feedback = feedback_df['feedback_count'].sum()
        st.metric("Total Feedback", int(total_feedback))
    
    with col2:
        avg_rating = feedback_df['avg_rating'].mean()
        st.metric("Average Rating", f"{avg_rating:.2f}" if not pd.isna(avg_rating) else "N/A")
    
    with col3:
        satisfaction_rate = (feedback_df['positive_feedback'].sum() / 
                           total_feedback * 100) if total_feedback > 0 else 0
        st.metric("Satisfaction Rate", f"{satisfaction_rate:.1f}%")
    
    # Rating distribution by model
    st.write("### Model Ratings")
    
    fig = px.bar(
        feedback_df,
        x='model_name',
        y='avg_rating',
        color='provider',
        title="Average Ratings by Model",
        labels={'avg_rating': 'Average Rating', 'model_name': 'Model'}
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed feedback table
    st.write("### Feedback Details")
    
    display_cols = ['model_name', 'provider', 'feedback_count', 'avg_rating', 
                   'positive_feedback', 'negative_feedback']
    display_df = feedback_df[display_cols].copy()
    display_df['avg_rating'] = display_df['avg_rating'].round(2)
    
    st.dataframe(display_df, use_container_width=True)