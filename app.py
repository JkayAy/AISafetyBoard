"""
AI Safety Benchmark Leaderboard - Streamlit Web Interface
Main application file for the web interface.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json
from database import Database
from utils import format_score, get_metric_description
import time

# Configure page
st.set_page_config(
    page_title="AI Safety Benchmark Leaderboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
@st.cache_resource
def get_database():
    """Initialize and return database connection."""
    return Database()

db = get_database()

def main():
    """Main application function."""
    st.title("🛡️ AI Safety Benchmark Leaderboard")
    st.markdown("Evaluating Large Language Models for Safety and Performance")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Leaderboard", "Model Details", "Submit Model", "Run Tests", "API Documentation"]
    )
    
    if page == "Leaderboard":
        show_leaderboard()
    elif page == "Model Details":
        show_model_details()
    elif page == "Submit Model":
        show_submit_model()
    elif page == "Run Tests":
        show_run_tests()
    elif page == "API Documentation":
        show_api_documentation()

def show_leaderboard():
    """Display the main leaderboard page."""
    st.header("🏆 Safety Benchmark Leaderboard")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("🔍 Search models", placeholder="Enter model name...")
    
    with col2:
        sort_metric = st.selectbox(
            "Sort by",
            ["Overall Score", "Hallucination Score", "Jailbreak Score", "Bias Score", "Last Updated"]
        )
    
    with col3:
        sort_order = st.selectbox("Order", ["Descending", "Ascending"])
    
    # Load results from database
    results = db.get_leaderboard_data()
    
    if not results:
        st.warning("No benchmark results available. Submit a model and run tests to see results.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Apply search filter
    if search_term:
        df = df[df['model_name'].str.contains(search_term, case=False, na=False)]
    
    # Apply sorting
    sort_column_map = {
        "Overall Score": "overall_score",
        "Hallucination Score": "hallucination_score",
        "Jailbreak Score": "jailbreak_score",
        "Bias Score": "bias_score",
        "Last Updated": "last_updated"
    }
    
    sort_col = sort_column_map[sort_metric]
    ascending = sort_order == "Ascending"
    df = df.sort_values(by=sort_col, ascending=ascending)
    
    # Display summary statistics
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Models", len(df))
        
        with col2:
            avg_overall = df['overall_score'].mean()
            st.metric("Average Overall Score", f"{avg_overall:.2f}")
        
        with col3:
            top_model = df.iloc[0]['model_name'] if not df.empty else "N/A"
            st.metric("Top Model", top_model)
        
        with col4:
            total_tests = len(results)
            st.metric("Total Test Runs", total_tests)
    
    # Display leaderboard table
    st.subheader("📊 Results")
    
    if df.empty:
        st.info("No models match your search criteria.")
        return
    
    # Format the dataframe for display
    display_df = df.copy()
    display_df['Overall Score'] = display_df['overall_score'].apply(lambda x: f"{x:.2f}")
    display_df['Hallucination Score'] = display_df['hallucination_score'].apply(lambda x: f"{x:.2f}")
    display_df['Jailbreak Score'] = display_df['jailbreak_score'].apply(lambda x: f"{x:.2f}")
    display_df['Bias Score'] = display_df['bias_score'].apply(lambda x: f"{x:.2f}")
    display_df['Last Updated'] = pd.to_datetime(display_df['last_updated']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Select columns for display
    display_columns = ['model_name', 'provider', 'Overall Score', 'Hallucination Score', 
                      'Jailbreak Score', 'Bias Score', 'Last Updated']
    
    st.dataframe(
        display_df[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "model_name": "Model Name",
            "provider": "Provider",
            "Last Updated": st.column_config.DatetimeColumn("Last Updated")
        }
    )
    
    # Export options
    st.subheader("📥 Export Data")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Export as CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"ai_safety_leaderboard_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📋 Export as JSON"):
            json_data = df.to_json(orient='records', indent=2)
            st.download_button(
                label="Download JSON",
                data=json_data.encode('utf-8'),
                file_name=f"ai_safety_leaderboard_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

def show_model_details():
    """Display detailed information about a specific model."""
    st.header("🔍 Model Details")
    
    # Get list of models
    models = db.get_all_models()
    
    if not models:
        st.warning("No models available. Submit a model first.")
        return
    
    model_names = [f"{model['name']} ({model['provider']})" for model in models]
    selected_model = st.selectbox("Select a model", model_names)
    
    if not selected_model:
        return
    
    # Parse selected model
    model_name = selected_model.split(" (")[0]
    model_info = next(model for model in models if model['name'] == model_name)
    
    # Display model information
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Model Information")
        st.write(f"**Name:** {model_info['name']}")
        st.write(f"**Provider:** {model_info['provider']}")
        st.write(f"**Version:** {model_info.get('version', 'N/A')}")
        st.write(f"**Created:** {model_info['created_at']}")
    
    with col2:
        st.subheader("🔗 API Configuration")
        st.write(f"**Endpoint:** {model_info.get('api_endpoint', 'Default')}")
        if model_info.get('description'):
            st.write(f"**Description:** {model_info['description']}")
    
    # Get historical results for this model
    results = db.get_model_results(model_info['id'])
    
    if not results:
        st.warning("No test results available for this model.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # Display performance charts
    st.subheader("📈 Performance Trends")
    
    # Create line chart for scores over time
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['created_at'],
        y=df['overall_score'],
        mode='lines+markers',
        name='Overall Score',
        line=dict(color='blue', width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['created_at'],
        y=df['hallucination_score'],
        mode='lines+markers',
        name='Hallucination Score',
        line=dict(color='red', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['created_at'],
        y=df['jailbreak_score'],
        mode='lines+markers',
        name='Jailbreak Score',
        line=dict(color='orange', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['created_at'],
        y=df['bias_score'],
        mode='lines+markers',
        name='Bias Score',
        line=dict(color='green', width=2)
    ))
    
    fig.update_layout(
        title="Safety Scores Over Time",
        xaxis_title="Date",
        yaxis_title="Score",
        yaxis=dict(range=[0, 100]),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display recent test results
    st.subheader("📊 Recent Test Results")
    
    if len(df) > 0:
        latest_result = df.iloc[-1]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Overall Score", f"{latest_result['overall_score']:.2f}")
        
        with col2:
            st.metric("Hallucination Score", f"{latest_result['hallucination_score']:.2f}")
        
        with col3:
            st.metric("Jailbreak Score", f"{latest_result['jailbreak_score']:.2f}")
        
        with col4:
            st.metric("Bias Score", f"{latest_result['bias_score']:.2f}")
        
        # Display example outputs if available
        if latest_result.get('example_outputs'):
            st.subheader("📝 Example Outputs")
            try:
                examples = json.loads(latest_result['example_outputs'])
                
                for test_type, output in examples.items():
                    with st.expander(f"{test_type.title()} Test Example"):
                        st.text(output)
            except json.JSONDecodeError:
                st.error("Could not parse example outputs.")

def show_submit_model():
    """Display model submission form."""
    st.header("📤 Submit New Model")
    st.markdown("Add a new model to the benchmark leaderboard.")
    
    with st.form("submit_model_form"):
        st.subheader("Model Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            model_name = st.text_input("Model Name*", placeholder="e.g., gpt-4o")
            provider = st.selectbox("Provider*", ["openai", "anthropic", "cohere", "huggingface"])
        
        with col2:
            version = st.text_input("Version", placeholder="e.g., 2024-05-13")
            api_endpoint = st.text_input("API Endpoint", placeholder="Leave empty for default")
        
        description = st.text_area("Description", placeholder="Optional description of the model")
        
        # API Configuration section
        st.subheader("API Configuration")
        st.info("API keys are managed through environment variables. Ensure the appropriate key is set for your selected provider.")
        
        submitted = st.form_submit_button("Submit Model", type="primary")
        
        if submitted:
            if not model_name or not provider:
                st.error("Model name and provider are required.")
                return
            
            try:
                # Submit via API
                api_url = "http://localhost:8000/submit"
                payload = {
                    "name": model_name,
                    "provider": provider,
                    "version": version or None,
                    "api_endpoint": api_endpoint or None,
                    "description": description or None
                }
                
                response = requests.post(api_url, json=payload)
                
                if response.status_code == 200:
                    st.success("Model submitted successfully!")
                    st.info("You can now run tests on this model from the 'Run Tests' page.")
                    time.sleep(2)
                    st.rerun()
                else:
                    error_msg = response.json().get('detail', 'Unknown error')
                    st.error(f"Submission failed: {error_msg}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to API server. Please ensure the server is running.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

def show_run_tests():
    """Display test execution interface."""
    st.header("🧪 Run Safety Tests")
    st.markdown("Execute safety benchmarks on submitted models.")
    
    # Get list of models
    models = db.get_all_models()
    
    if not models:
        st.warning("No models available. Submit a model first.")
        return
    
    with st.form("run_tests_form"):
        st.subheader("Test Configuration")
        
        # Model selection
        model_options = [f"{model['name']} ({model['provider']})" for model in models]
        selected_models = st.multiselect("Select Models", model_options, default=model_options[:1])
        
        # Test selection
        st.subheader("Test Types")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            run_hallucination = st.checkbox("Hallucination Test", value=True)
            st.caption(get_metric_description("hallucination"))
        
        with col2:
            run_jailbreak = st.checkbox("Jailbreak Resistance Test", value=True)
            st.caption(get_metric_description("jailbreak"))
        
        with col3:
            run_bias = st.checkbox("Bias Detection Test", value=True)
            st.caption(get_metric_description("bias"))
        
        # Admin authentication
        st.subheader("Authentication")
        admin_key = st.text_input("Admin API Key", type="password", 
                                 help="Required to run tests")
        
        submitted = st.form_submit_button("Run Tests", type="primary")
        
        if submitted:
            if not selected_models:
                st.error("Please select at least one model.")
                return
            
            if not (run_hallucination or run_jailbreak or run_bias):
                st.error("Please select at least one test type.")
                return
            
            if not admin_key:
                st.error("Admin API key is required.")
                return
            
            # Run tests via API
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                for i, selected_model in enumerate(selected_models):
                    model_name = selected_model.split(" (")[0]
                    
                    status_text.text(f"Running tests for {model_name}...")
                    
                    # Find model ID
                    model_info = next(model for model in models if model['name'] == model_name)
                    
                    api_url = "http://localhost:8000/run-tests"
                    payload = {
                        "model_id": model_info['id'],
                        "run_hallucination": run_hallucination,
                        "run_jailbreak": run_jailbreak,
                        "run_bias": run_bias
                    }
                    
                    headers = {"X-Admin-Key": admin_key}
                    response = requests.post(api_url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        st.success(f"Tests completed for {model_name}")
                    else:
                        error_msg = response.json().get('detail', 'Unknown error')
                        st.error(f"Tests failed for {model_name}: {error_msg}")
                    
                    progress_bar.progress((i + 1) / len(selected_models))
                
                status_text.text("All tests completed!")
                st.info("Check the leaderboard for updated results.")
                
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to API server. Please ensure the server is running.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

def show_api_documentation():
    """Display API documentation."""
    st.header("📚 API Documentation")
    st.markdown("Public API endpoints for programmatic access to the leaderboard.")
    
    # Base URL
    st.subheader("Base URL")
    st.code("http://localhost:8000", language="text")
    
    # Endpoints documentation
    st.subheader("Endpoints")
    
    # GET /results
    with st.expander("GET /results - Retrieve leaderboard data"):
        st.markdown("""
        **Description:** Get all benchmark results in JSON format.
        
        **Parameters:**
        - `limit` (optional): Maximum number of results to return
        - `model_name` (optional): Filter by model name
        
        **Response:**
        ```json
        [
            {
                "model_name": "gpt-4o",
                "provider": "openai",
                "overall_score": 85.5,
                "hallucination_score": 90.0,
                "jailbreak_score": 82.0,
                "bias_score": 84.5,
                "last_updated": "2024-01-15T10:30:00Z"
            }
        ]
        ```
        """)
        
        st.code("curl -X GET 'http://localhost:8000/results?limit=10'", language="bash")
    
    # POST /submit
    with st.expander("POST /submit - Submit new model"):
        st.markdown("""
        **Description:** Submit a new model for benchmarking.
        
        **Request Body:**
        ```json
        {
            "name": "gpt-4o",
            "provider": "openai",
            "version": "2024-05-13",
            "api_endpoint": null,
            "description": "Latest GPT-4 model"
        }
        ```
        
        **Response:**
        ```json
        {
            "message": "Model submitted successfully",
            "model_id": 1
        }
        ```
        """)
        
        st.code("curl -X POST 'http://localhost:8000/submit' -H 'Content-Type: application/json' -d '{\"name\":\"gpt-4o\",\"provider\":\"openai\"}'", language="bash")
    
    # POST /run-tests
    with st.expander("POST /run-tests - Run tests (Admin only)"):
        st.markdown("""
        **Description:** Execute safety tests on a model.
        
        **Headers:**
        - `X-Admin-Key`: Admin API key for authentication
        
        **Request Body:**
        ```json
        {
            "model_id": 1,
            "run_hallucination": true,
            "run_jailbreak": true,
            "run_bias": true
        }
        ```
        
        **Response:**
        ```json
        {
            "message": "Tests completed successfully",
            "result_id": 1,
            "scores": {
                "overall_score": 85.5,
                "hallucination_score": 90.0,
                "jailbreak_score": 82.0,
                "bias_score": 84.5
            }
        }
        ```
        """)
        
        st.code("curl -X POST 'http://localhost:8000/run-tests' -H 'X-Admin-Key: your-admin-key' -H 'Content-Type: application/json' -d '{\"model_id\":1}'", language="bash")
    
    # Usage examples
    st.subheader("Usage Examples")
    
    st.markdown("**Python Example:**")
    st.code("""
import requests

# Get leaderboard data
response = requests.get('http://localhost:8000/results')
data = response.json()

# Submit new model
model_data = {
    "name": "claude-3-sonnet",
    "provider": "anthropic",
    "description": "Anthropic's Claude 3 Sonnet model"
}
response = requests.post('http://localhost:8000/submit', json=model_data)
    """, language="python")
    
    st.markdown("**JavaScript Example:**")
    st.code("""
// Get leaderboard data
fetch('http://localhost:8000/results')
  .then(response => response.json())
  .then(data => console.log(data));

// Submit new model
fetch('http://localhost:8000/submit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'claude-3-sonnet',
    provider: 'anthropic'
  })
});
    """, language="javascript")

if __name__ == "__main__":
    main()