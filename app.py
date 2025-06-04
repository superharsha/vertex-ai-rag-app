#!/usr/bin/env python3

import streamlit as st
import os
import json
import tempfile
from datetime import datetime

# Set page config first
st.set_page_config(
    page_title="🤖 Document Query System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Google Cloud imports
import vertexai
from vertexai import rag
from vertexai.generative_models import GenerativeModel, Tool

# Custom CSS
st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #1f4e79, #2e7bcf);
    padding: 2rem;
    border-radius: 15px;
    color: white;
    margin-bottom: 2rem;
    text-align: center;
}
.query-container {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 15px;
    padding: 2rem;
    margin: 2rem 0;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    color: #333333;
}
.response-container {
    background: white;
    border-radius: 10px;
    padding: 1.5rem;
    margin: 1rem 0;
    border-left: 4px solid #28a745;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    color: #333333;
}
.status-indicator {
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-weight: bold;
    margin: 0.5rem 0;
    color: #333333;
}
.status-ready {
    background-color: #d4edda;
    color: #155724 !important;
    border: 1px solid #c3e6cb;
}
.status-error {
    background-color: #f8d7da;
    color: #721c24 !important;
    border: 1px solid #f5c6cb;
}
.footer-stats {
    background-color: #f8f9fa;
    border-radius: 10px;
    padding: 1rem;
    margin-top: 2rem;
    text-align: center;
    color: #333333;
}
/* Fix text color in main content */
.main .block-container {
    color: #333333;
}
/* Fix text color in text areas and inputs */
.stTextArea > div > div > textarea {
    color: #333333;
    background-color: #ffffff;
}
.stTextInput > div > div > input {
    color: #333333;
    background-color: #ffffff;
}
/* Fix selectbox and other components */
.stSelectbox > div > div > div {
    color: #333333;
    background-color: #ffffff;
}
/* Fix expander content */
.streamlit-expanderContent {
    background-color: #ffffff;
    color: #333333;
}
/* Fix radio buttons */
.stRadio > div {
    color: #333333;
}
</style>
""", unsafe_allow_html=True)

# Constants
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or "vpc-host-nonprod-kk186-dr143"
LOCATION = "us-central1"

# Available models
AVAILABLE_MODELS = {
    "Gemini 2.0 Flash": "gemini-2.0-flash-001",
    "Gemini 2.5 Flash Preview": "gemini-2.5-flash-preview-0514"
}

def setup_google_credentials():
    """Setup Google Cloud credentials for Streamlit Cloud deployment"""
    try:
        # For local development: Check environment variables FIRST
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            expanded_path = os.path.expanduser(creds_path)
            
            if os.path.exists(expanded_path):
                return True, f"Using service account key from: {creds_path}"
            else:
                return False, f"Credentials file not found: {expanded_path}"
        
        # For Streamlit Cloud: Use Streamlit secrets (only if env vars not set)
        elif hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            # Check if secrets contain real values (not placeholders)
            service_account_info = dict(st.secrets["gcp_service_account"])
            
            # Check if it's a placeholder
            if "your-private-key-id-here" in service_account_info.get("private_key_id", ""):
                return False, "Streamlit secrets contain placeholder values. Please update with real credentials."
            
            # Write credentials to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(service_account_info, f)
                temp_creds_path = f.name
            
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_path
            return True, f"Using Streamlit secrets for authentication"
        
        # Try Application Default Credentials
        else:
            try:
                from google.auth import default
                credentials, project = default()
                if credentials and project:
                    return True, f"Using Application Default Credentials for project: {project}"
            except Exception:
                pass
        
        return False, "No valid credentials found. Please set GOOGLE_APPLICATION_CREDENTIALS environment variable or configure Streamlit secrets."
                
    except Exception as e:
        return False, f"Failed to setup credentials: {str(e)}"

@st.cache_data(show_spinner="🔍 Loading knowledge base...")
def load_corpus():
    """Load existing corpus for querying"""
    
    # Setup credentials
    creds_success, creds_msg = setup_google_credentials()
    if not creds_success:
        st.error(f"❌ Authentication failed: {creds_msg}")
        if not hasattr(st, 'secrets') or 'gcp_service_account' not in st.secrets:
            st.info("💡 **For Streamlit Cloud:** Add your Google Cloud service account JSON to Streamlit secrets as 'gcp_service_account'")
        st.stop()
    
    if not PROJECT_ID:
        st.error("❌ PROJECT_ID not found in environment")
        st.stop()
    
    # Initialize Vertex AI
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        st.error(f"❌ Failed to initialize Vertex AI: {str(e)}")
        st.stop()
    
    # Use hardcoded corpus name for deployment (since corpus_name.txt may not exist in cloud)
    corpus_name = "projects/315883473892/locations/us-central1/ragCorpora/2738188573441261568"
    
    # Get corpus object
    try:
        corpus = rag.get_corpus(name=corpus_name)
        return {
            'corpus': corpus,
            'corpus_name': corpus_name,
            'status': 'ready'
        }
    except Exception as e:
        st.error(f"❌ Failed to load corpus: {str(e)}")
        st.error("💡 **Solution:** The knowledge base may need to be recreated or the corpus ID updated")
        st.stop()

def query_documents_direct(corpus_name: str, query: str, top_k: int = 5) -> tuple[bool, str]:
    """Direct context retrieval following Google documentation"""
    try:
        # Direct context retrieval
        rag_retrieval_config = rag.RagRetrievalConfig(
            top_k=top_k,  # Optional
            filter=rag.Filter(vector_distance_threshold=0.5),  # Optional
        )
        
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=corpus_name,
                )
            ],
            text=query,
            rag_retrieval_config=rag_retrieval_config,
        )
        
        return True, str(response)
    except Exception as e:
        return False, f"Direct retrieval failed: {str(e)}"

def query_documents_enhanced(corpus_name: str, query: str, model_name: str, top_k: int = 5, system_prompt: str = None) -> tuple[bool, str]:
    """Enhanced generation following Google documentation exactly"""
    try:
        # RAG retrieval configuration  
        rag_retrieval_config = rag.RagRetrievalConfig(
            top_k=top_k,  # Optional
            filter=rag.Filter(vector_distance_threshold=0.5),  # Optional
        )
        
        # Create a RAG retrieval tool
        rag_retrieval_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        rag.RagResource(
                            rag_corpus=corpus_name,  # Currently only 1 corpus is allowed.
                        )
                    ],
                    rag_retrieval_config=rag_retrieval_config,
                ),
            )
        )

        # Create a Gemini model instance with optional system instruction
        if system_prompt and system_prompt.strip():
            rag_model = GenerativeModel(
                model_name=model_name, 
                tools=[rag_retrieval_tool],
                system_instruction=system_prompt.strip()
            )
        else:
            rag_model = GenerativeModel(
                model_name=model_name, 
                tools=[rag_retrieval_tool]
            )

        # Generate response
        response = rag_model.generate_content(query)
        return True, response.text
        
    except Exception as e:
        return False, f"Enhanced generation failed: {str(e)}"

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Document Query System</h1>
        <p>Powered by Google Vertex AI RAG Engine • Query your knowledge base</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load corpus (cached)
    try:
        system_info = load_corpus()
        
        # Show system status
        st.markdown(f"""
        <div class="status-indicator status-ready">
            ✅ Knowledge Base Ready • Corpus: {system_info['corpus_name'].split('/')[-1]}
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.markdown(f"""
        <div class="status-indicator status-error">
            ❌ Knowledge Base Error • Check configuration
        </div>
        """, unsafe_allow_html=True)
        st.error(f"System initialization failed: {str(e)}")
        st.stop()
    
    # Main query interface
    st.markdown("""
    <div class="query-container">
        <h2 style="margin-top: 0;">🔍 Ask Your Question</h2>
        <p>Query your document collection using natural language</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Query input
    query = st.text_area(
        "Enter your question:",
        placeholder="What would you like to know about your documents?",
        height=120
    )
    
    # Advanced settings
    with st.expander("🎛️ Advanced Settings"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Model selection
            selected_model = st.selectbox(
                "🤖 AI Model:",
                options=list(AVAILABLE_MODELS.keys()),
                index=0,
                help="Choose which Gemini model to use for generation"
            )
            
            preset_prompts = {
                "Default": "",
                "📊 Analytical Expert": "You are an analytical expert. Provide detailed, structured responses with clear reasoning and evidence from the documents. Include specific examples and data points when available.",
                "📋 Executive Summary": "You are an executive assistant. Provide concise, high-level summaries focusing on key business insights, decisions, and strategic implications from the documents.",
                "🔧 Technical Specialist": "You are a technical specialist. Focus on technical details, specifications, processes, and provide in-depth technical explanations based on the document content.",
                "📅 Project Manager": "You are a project management expert. Focus on timelines, deliverables, risks, resources, and project-related information from the documents.",
                "💰 Financial Analyst": "You are a financial analyst. Focus on costs, budgets, financial implications, ROI, and economic factors mentioned in the documents.",
                "⚖️ Compliance Officer": "You are a compliance expert. Focus on regulations, standards, requirements, and compliance-related information from the documents."
            }
            
            selected_preset = st.selectbox(
                "Response Style:",
                options=list(preset_prompts.keys()),
                help="Choose how the AI should respond"
            )
        
        with col2:
            top_k = st.slider("Document Depth", 1, 10, 5, help="Number of document sections to analyze")
        
        # Query method selection
        query_method = st.radio(
            "Query Method:",
            ["Enhanced Generation (Recommended)", "Direct Retrieval"],
            help="Enhanced Generation uses Gemini with system prompts. Direct Retrieval shows raw context."
        )
        
        # Custom prompt (only for enhanced generation)
        if query_method == "Enhanced Generation (Recommended)":
            if selected_preset != "Default":
                system_prompt = preset_prompts[selected_preset]
                st.info(f"Using: {selected_preset}")
            else:
                system_prompt = st.text_area(
                    "Custom Instructions (Optional):",
                    height=80,
                    placeholder="Tell the AI how to respond to your questions..."
                )
        else:
            system_prompt = None
    
    # Query execution
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_button = st.button("🔍 Search Documents", type="primary", use_container_width=True)
    
    if search_button and query.strip():
        with st.spinner("🧠 Analyzing documents..."):
            if query_method == "Enhanced Generation (Recommended)":
                success, response = query_documents_enhanced(
                    system_info['corpus_name'], 
                    query.strip(), 
                    AVAILABLE_MODELS[selected_model], 
                    top_k=top_k, 
                    system_prompt=system_prompt if system_prompt and system_prompt.strip() else None
                )
            else:
                success, response = query_documents_direct(
                    system_info['corpus_name'], 
                    query.strip(), 
                    top_k=top_k
                )
            
            if success:
                st.markdown("""
                <div class="response-container">
                    <h3 style="margin-top: 0; color: #28a745;">📋 Response</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(response)
                
                # Timestamp
                st.caption(f"Query executed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} using {query_method}")
            else:
                st.error(f"❌ {response}")
    
    elif search_button:
        st.warning("⚠️ Please enter a question to search.")
    
    # Footer info
    st.markdown(f"""
    <div class="footer-stats">
        <strong>🤖 AI Model:</strong> {selected_model}<br>
        <strong>🧠 Knowledge Base:</strong> {system_info['corpus_name'].split('/')[-1]}<br>
        <strong>🏗️ Status:</strong> Ready for queries<br>
        <strong>📚 Embedding Model:</strong> text-embedding-005<br>
        <strong>📁 Documents:</strong> 56 files processed
    </div>
    """, unsafe_allow_html=True)
    
    # Instructions in sidebar
    with st.sidebar:
        st.markdown("### 🛠️ Knowledge Base Management")
        st.markdown("""
        This app connects to a pre-built knowledge base containing 56 documents covering:
        - HealthSync project documentation
        - RFP documents and requirements
        - Business reports and contracts
        - Technical specifications
        """)
        
        st.markdown("### 📊 System Info")
        st.info(f"**Project:** {PROJECT_ID}")
        st.info(f"**Location:** {LOCATION}")
        st.info(f"**Corpus:** {system_info['corpus_name'].split('/')[-1]}")
        
        st.markdown("### 🎯 Query Methods")
        st.markdown("""
        **Enhanced Generation:** Uses Gemini 2.0 Flash with RAG retrieval tool and system prompts
        
        **Direct Retrieval:** Shows raw retrieved context from documents
        """)
        
        st.markdown("### 💡 Sample Queries")
        st.markdown("""
        - "What are the key requirements in the HealthSync project?"
        - "Summarize financial information about Valenbridge Global"
        - "What are the main risks across all projects?"
        - "Show me technical specifications from RFP documents"
        """)

if __name__ == "__main__":
    main() 