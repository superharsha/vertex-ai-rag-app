#!/usr/bin/env python3
"""
Standalone Streamlit App for Vertex AI RAG System
Ready for Streamlit Cloud deployment
"""

import streamlit as st
import logging
import tempfile
import uuid
import os
import glob
from datetime import datetime
from typing import Tuple
import time

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
from google.cloud import storage
from google.cloud.exceptions import NotFound, Conflict

# Document processing imports
try:
    import PyPDF2
    import docx
    PDF_DOCX_AVAILABLE = True
except ImportError:
    PDF_DOCX_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
}
.response-container {
    background: white;
    border-radius: 10px;
    padding: 1.5rem;
    margin: 1rem 0;
    border-left: 4px solid #28a745;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.status-indicator {
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-weight: bold;
    margin: 0.5rem 0;
}
.status-ready {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}
.status-processing {
    background-color: #fff3cd;
    color: #856404;
    border: 1px solid #ffeaa7;
}
.footer-stats {
    background-color: #f8f9fa;
    border-radius: 10px;
    padding: 1rem;
    margin-top: 2rem;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# Constants
DOCUMENTS_FOLDER = "/Users/sr/Downloads/All Files"
CORPUS_NAME = "knowledge-base"
PROJECT_ID = st.secrets.get("PROJECT_ID", "")
LOCATION = "us-central1"
GENERATION_MODEL = "gemini-2.0-flash-001"

def setup_google_credentials():
    """Setup Google Cloud credentials from Streamlit secrets"""
    try:
        if hasattr(st, 'secrets') and "service_account" in st.secrets:
            import json
            import os
            from google.oauth2 import service_account
            
            # Create credentials from Streamlit secrets
            creds_dict = dict(st.secrets["service_account"])
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            
            # Set environment variable for Google Cloud authentication
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/service_account.json"
            with open("/tmp/service_account.json", "w") as f:
                json.dump(creds_dict, f)
            
            return True, "Credentials configured successfully"
        else:
            return False, "No service account credentials found in secrets"
    except Exception as e:
        return False, f"Failed to setup credentials: {str(e)}"

def extract_text_from_pdf(file_content) -> str:
    """Extract text from PDF file"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(file_content)
            tmp_file.flush()
            
            with open(tmp_file.name, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n"
                
                os.unlink(tmp_file.name)
                return text
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"

def extract_text_from_docx(file_content) -> str:
    """Extract text from DOCX file"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
            tmp_file.write(file_content)
            tmp_file.flush()
            
            doc = docx.Document(tmp_file.name)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
            os.unlink(tmp_file.name)
            return text
    except Exception as e:
        return f"Error extracting DOCX text: {str(e)}"

@st.cache_data(show_spinner="🚀 Initializing document processing system...")
def initialize_system():
    """Initialize the entire RAG system and process all documents"""
    
    # Setup credentials
    creds_success, creds_msg = setup_google_credentials()
    if not creds_success:
        st.error(f"❌ Authentication failed: {creds_msg}")
        st.stop()
    
    if not PROJECT_ID:
        st.error("❌ PROJECT_ID not found in secrets")
        st.stop()
    
    # Initialize Vertex AI
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        storage_client = storage.Client(project=PROJECT_ID)
        bucket_name = f"{PROJECT_ID}-knowledge-base-docs"
    except Exception as e:
        st.error(f"❌ Failed to initialize Google Cloud: {str(e)}")
        st.stop()
    
    # Create/get bucket
    try:
        bucket = storage_client.bucket(bucket_name)
        if not bucket.exists():
            bucket = storage_client.create_bucket(bucket_name, location=LOCATION)
    except Exception as e:
        st.error(f"❌ Failed to setup storage: {str(e)}")
        st.stop()
    
    # Create corpus
    try:
        corpus_display_name = f"{CORPUS_NAME}-{uuid.uuid4().hex[:8]}"
        corpus = rag.create_corpus(display_name=corpus_display_name)
    except Exception as e:
        st.error(f"❌ Failed to create knowledge base: {str(e)}")
        st.stop()
    
    # Process documents
    if not os.path.exists(DOCUMENTS_FOLDER):
        st.error(f"❌ Documents folder not found: {DOCUMENTS_FOLDER}")
        st.stop()
    
    # Get all files
    file_patterns = ['*.pdf', '*.docx', '*.txt', '*.md']
    all_files = []
    for pattern in file_patterns:
        all_files.extend(glob.glob(os.path.join(DOCUMENTS_FOLDER, pattern)))
    
    if not all_files:
        st.error("❌ No documents found to process")
        st.stop()
    
    processed_count = 0
    failed_files = []
    
    # Process each file
    for file_path in all_files:
        try:
            filename = os.path.basename(file_path)
            blob_name = f"{uuid.uuid4().hex}_{filename}"
            blob = bucket.blob(blob_name)
            
            # Process file based on type
            if file_path.lower().endswith('.pdf'):
                if PDF_DOCX_AVAILABLE:
                    with open(file_path, 'rb') as f:
                        text_content = extract_text_from_pdf(f.read())
                    blob.upload_from_string(text_content.encode('utf-8'), content_type="text/plain")
                    blob_name = blob_name.replace('.pdf', '.txt')
                else:
                    failed_files.append(filename)
                    continue
            elif file_path.lower().endswith('.docx'):
                if PDF_DOCX_AVAILABLE:
                    with open(file_path, 'rb') as f:
                        text_content = extract_text_from_docx(f.read())
                    blob.upload_from_string(text_content.encode('utf-8'), content_type="text/plain")
                    blob_name = blob_name.replace('.docx', '.txt')
                else:
                    failed_files.append(filename)
                    continue
            elif file_path.lower().endswith(('.txt', '.md')):
                blob.upload_from_filename(file_path, content_type="text/plain")
            else:
                failed_files.append(filename)
                continue
            
            # Import to corpus
            gcs_uri = f"gs://{bucket_name}/{blob_name}"
            rag.import_files(
                corpus.name,
                [gcs_uri],
                max_embedding_requests_per_min=100,
            )
            processed_count += 1
            
        except Exception as e:
            failed_files.append(f"{filename}: {str(e)}")
            continue
    
    return {
        'corpus': corpus,
        'bucket_name': bucket_name,
        'processed_count': processed_count,
        'total_files': len(all_files),
        'failed_files': failed_files
    }

def query_documents(corpus, query: str, top_k: int = 5, system_prompt: str = None) -> tuple[bool, str]:
    """Query the RAG corpus"""
    try:
        # Create RAG tool
        retrieval = rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[rag.RagResource(rag_corpus=corpus.name)],
                rag_retrieval_config=rag.RagRetrievalConfig(top_k=top_k)
            ),
        )
        
        rag_tool = Tool.from_retrieval(retrieval=retrieval)
        
        # Create model with optional system instruction
        if system_prompt and system_prompt.strip():
            model = GenerativeModel(
                model_name=GENERATION_MODEL,
                tools=[rag_tool],
                system_instruction=system_prompt.strip()
            )
        else:
            model = GenerativeModel(
                model_name=GENERATION_MODEL,
                tools=[rag_tool]
            )
        
        response = model.generate_content(query)
        return True, response.text
    except Exception as e:
        return False, f"Query failed: {str(e)}"

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Document Query System</h1>
        <p>Powered by Google Vertex AI • Ready to answer your questions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize system (cached)
    system_info = initialize_system()
    
    # Show system status
    st.markdown(f"""
    <div class="status-indicator status-ready">
        ✅ System Ready • {system_info['processed_count']}/{system_info['total_files']} documents processed
    </div>
    """, unsafe_allow_html=True)
    
    # Main query interface
    st.markdown("""
    <div class="query-container">
        <h2 style="margin-top: 0;">🔍 Ask Your Question</h2>
        <p>Query your document collection using natural language</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Query input
    query = st.text_area(
        "",
        placeholder="What would you like to know about your documents?",
        height=120,
        label_visibility="collapsed"
    )
    
    # Advanced settings
    with st.expander("🎛️ Advanced Settings"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
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
        
        # Custom prompt
        if selected_preset != "Default":
            system_prompt = preset_prompts[selected_preset]
            st.info(f"Using: {selected_preset}")
        else:
            system_prompt = st.text_area(
                "Custom Instructions (Optional):",
                height=80,
                placeholder="Tell the AI how to respond to your questions..."
            )
    
    # Query execution
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_button = st.button("🔍 Search Documents", type="primary", use_container_width=True)
    
    if search_button and query.strip():
        with st.spinner("🧠 Analyzing documents..."):
            success, response = query_documents(
                system_info['corpus'], 
                query.strip(), 
                top_k=top_k, 
                system_prompt=system_prompt if system_prompt.strip() else None
            )
            
            if success:
                st.markdown("""
                <div class="response-container">
                    <h3 style="margin-top: 0; color: #28a745;">📋 Response</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(response)
                
                # Timestamp
                st.caption(f"Query executed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                st.error(f"❌ {response}")
    
    elif search_button:
        st.warning("⚠️ Please enter a question to search.")
    
    # Footer info
    st.markdown(f"""
    <div class="footer-stats">
        <strong>📁 Document Source:</strong> {DOCUMENTS_FOLDER}<br>
        <strong>🤖 AI Model:</strong> {GENERATION_MODEL}<br>
        <strong>📊 Documents Processed:</strong> {system_info['processed_count']} files
    </div>
    """, unsafe_allow_html=True)
    
    # Show failed files if any (in sidebar)
    if system_info['failed_files']:
        with st.sidebar:
            st.warning(f"⚠️ {len(system_info['failed_files'])} files failed to process")
            with st.expander("View failed files"):
                for failed_file in system_info['failed_files']:
                    st.write(f"• {failed_file}")

if __name__ == "__main__":
    main() 