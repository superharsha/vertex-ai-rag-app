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

# Set page config first
st.set_page_config(
    page_title="🤖 Vertex AI Document Query System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
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
    padding: 1rem;
    border-radius: 10px;
    color: white;
    margin-bottom: 2rem;
}
.success-box {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 5px;
    padding: 10px;
    margin: 10px 0;
}
.error-box {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    border-radius: 5px;
    padding: 10px;
    margin: 10px 0;
}
.info-box {
    background-color: #d1ecf1;
    border: 1px solid #bee5eb;
    border-radius: 5px;
    padding: 10px;
    margin: 10px 0;
}
.query-box {
    background-color: #f8f9fa;
    border: 2px solid #e9ecef;
    border-radius: 10px;
    padding: 20px;
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

# Constants
DOCUMENTS_FOLDER = "/Users/sr/Downloads/All Files"
CORPUS_NAME = "all-files-knowledge-base"

class VertexAIRAGManager:
    def __init__(self):
        self.project_id = None
        self.location = None
        self.bucket_name = None
        self.generation_model = None
        self.corpus = None
        self.storage_client = None
        self.initialized = False
        self.documents_processed = False
    
    def initialize(self, project_id: str, location: str = "us-central1", 
                  generation_model: str = "gemini-2.0-flash-001"):
        """Initialize Vertex AI and GCS"""
        try:
            self.project_id = project_id
            self.location = location
            self.generation_model = generation_model
            self.bucket_name = f"{project_id}-all-files-rag-docs"
            
            # Initialize Vertex AI
            vertexai.init(project=project_id, location=location)
            
            # Initialize Storage client
            self.storage_client = storage.Client(project=project_id)
            
            self.initialized = True
            return True, "Vertex AI initialized successfully"
        except Exception as e:
            return False, f"Failed to initialize Vertex AI: {str(e)}"
    
    def create_bucket_if_not_exists(self) -> tuple[bool, str]:
        """Create GCS bucket if it doesn't exist"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(
                    self.bucket_name, 
                    location=self.location
                )
                return True, f"Created bucket: {self.bucket_name}"
            else:
                return True, f"Bucket already exists: {self.bucket_name}"
        except Exception as e:
            return False, f"Failed to create bucket: {str(e)}"
    
    def create_new_corpus(self) -> tuple[bool, str]:
        """Create a new RAG corpus for all files"""
        try:
            corpus_display_name = f"{CORPUS_NAME}-{uuid.uuid4().hex[:8]}"
            
            self.corpus = rag.create_corpus(
                display_name=corpus_display_name
            )
            return True, f"Created corpus: {self.corpus.name}"
        except Exception as e:
            return False, f"Failed to create corpus: {str(e)}"
    
    def upload_file_to_gcs(self, file_path: str) -> tuple[bool, str]:
        """Upload file to GCS bucket"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            filename = os.path.basename(file_path)
            blob_name = f"{uuid.uuid4().hex}_{filename}"
            blob = bucket.blob(blob_name)
            
            # Read and process file content
            if file_path.lower().endswith('.pdf'):
                if PDF_DOCX_AVAILABLE:
                    with open(file_path, 'rb') as f:
                        text_content = extract_text_from_pdf(f.read())
                    blob.upload_from_string(text_content.encode('utf-8'), content_type="text/plain")
                    blob_name = blob_name.replace('.pdf', '.txt')
                else:
                    return False, f"PDF processing not available for {filename}"
            elif file_path.lower().endswith('.docx'):
                if PDF_DOCX_AVAILABLE:
                    with open(file_path, 'rb') as f:
                        text_content = extract_text_from_docx(f.read())
                    blob.upload_from_string(text_content.encode('utf-8'), content_type="text/plain")
                    blob_name = blob_name.replace('.docx', '.txt')
                else:
                    return False, f"DOCX processing not available for {filename}"
            elif file_path.lower().endswith(('.txt', '.md')):
                blob.upload_from_filename(file_path, content_type="text/plain")
            else:
                return False, f"Unsupported file type: {filename}"
            
            gcs_uri = f"gs://{self.bucket_name}/{blob_name}"
            return True, gcs_uri
        except Exception as e:
            return False, f"Failed to upload {os.path.basename(file_path)}: {str(e)}"
    
    def import_document_to_corpus(self, gcs_uri: str) -> tuple[bool, str]:
        """Import document from GCS to RAG corpus"""
        try:
            rag.import_files(
                self.corpus.name,
                [gcs_uri],
                max_embedding_requests_per_min=100,
            )
            return True, f"Document imported successfully: {gcs_uri}"
        except Exception as e:
            return False, f"Failed to import document: {str(e)}"
    
    def process_all_documents(self) -> tuple[bool, str, list]:
        """Process all documents from the specified folder"""
        if not os.path.exists(DOCUMENTS_FOLDER):
            return False, f"Folder not found: {DOCUMENTS_FOLDER}", []
        
        # Get all supported files
        file_patterns = ['*.pdf', '*.docx', '*.txt', '*.md']
        all_files = []
        for pattern in file_patterns:
            all_files.extend(glob.glob(os.path.join(DOCUMENTS_FOLDER, pattern)))
        
        if not all_files:
            return False, "No supported documents found in folder", []
        
        processed_files = []
        failed_files = []
        
        for file_path in all_files:
            filename = os.path.basename(file_path)
            
            # Upload to GCS
            upload_success, gcs_uri_or_error = self.upload_file_to_gcs(file_path)
            
            if upload_success:
                # Import to corpus
                import_success, import_msg = self.import_document_to_corpus(gcs_uri_or_error)
                if import_success:
                    processed_files.append({
                        'name': filename,
                        'gcs_uri': gcs_uri_or_error,
                        'status': 'success'
                    })
                else:
                    failed_files.append({'name': filename, 'error': import_msg})
            else:
                failed_files.append({'name': filename, 'error': gcs_uri_or_error})
        
        self.documents_processed = True
        
        result_msg = f"Processed {len(processed_files)} documents successfully"
        if failed_files:
            result_msg += f", {len(failed_files)} failed"
        
        return True, result_msg, {'processed': processed_files, 'failed': failed_files}
    
    def query_documents(self, query: str, top_k: int = 5, system_prompt: str = None) -> tuple[bool, str]:
        """Query the RAG corpus with optional system prompt"""
        try:
            if not self.corpus:
                return False, "No corpus available. Please process documents first."
            
            # Create RAG tool
            retrieval = rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[rag.RagResource(rag_corpus=self.corpus.name)],
                    rag_retrieval_config=rag.RagRetrievalConfig(
                        top_k=top_k,
                    )
                ),
            )
            
            rag_tool = Tool.from_retrieval(retrieval=retrieval)
            
            # Create model with optional system instruction
            if system_prompt and system_prompt.strip():
                model = GenerativeModel(
                    model_name=self.generation_model,
                    tools=[rag_tool],
                    system_instruction=system_prompt.strip()
                )
            else:
                model = GenerativeModel(
                    model_name=self.generation_model,
                    tools=[rag_tool]
                )
            
            response = model.generate_content(query)
            return True, response.text
        except Exception as e:
            return False, f"Query failed: {str(e)}"

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

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Vertex AI Document Query System</h1>
        <p>Query pre-processed documents using Google's Vertex AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Setup credentials
    creds_success, creds_msg = setup_google_credentials()
    if not creds_success:
        st.error(f"❌ {creds_msg}")
        st.info("Please configure Google Cloud service account in Streamlit secrets.")
        st.stop()
    
    # Initialize session state
    if 'rag_manager' not in st.session_state:
        st.session_state.rag_manager = VertexAIRAGManager()
        st.session_state.processing_complete = False
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Project configuration
        project_id = st.text_input(
            "Google Cloud Project ID",
            value=st.secrets.get("PROJECT_ID", ""),
            help="Your Google Cloud Project ID"
        )
        
        location = st.selectbox(
            "Location",
            ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-southeast1"],
            index=0
        )
        
        generation_model = st.selectbox(
            "Generation Model",
            ["gemini-2.0-flash-001", "gemini-2.5-flash-preview-05-20", "gemini-1.5-pro", "gemini-1.5-flash"],
            index=0
        )
        
        # Initialize and process documents
        if st.button("🚀 Initialize & Process Documents", type="primary"):
            if not project_id:
                st.error("Please enter a Project ID")
            else:
                with st.spinner("Initializing Vertex AI..."):
                    success, msg = st.session_state.rag_manager.initialize(
                        project_id, location, generation_model
                    )
                    if success:
                        st.success(msg)
                        
                        # Create bucket
                        with st.spinner("Setting up storage..."):
                            bucket_success, bucket_msg = st.session_state.rag_manager.create_bucket_if_not_exists()
                            if bucket_success:
                                st.success(bucket_msg)
                            else:
                                st.error(bucket_msg)
                                st.stop()
                        
                        # Create new corpus
                        with st.spinner("Creating knowledge base..."):
                            corpus_success, corpus_msg = st.session_state.rag_manager.create_new_corpus()
                            if corpus_success:
                                st.success(corpus_msg)
                            else:
                                st.error(corpus_msg)
                                st.stop()
                        
                        # Process all documents
                        with st.spinner(f"Processing documents from {DOCUMENTS_FOLDER}..."):
                            process_success, process_msg, results = st.session_state.rag_manager.process_all_documents()
                            if process_success:
                                st.success(process_msg)
                                st.session_state.processing_complete = True
                                
                                # Show processing results
                                if results['processed']:
                                    st.write("✅ **Successfully processed:**")
                                    for doc in results['processed'][:5]:  # Show first 5
                                        st.write(f"- {doc['name']}")
                                    if len(results['processed']) > 5:
                                        st.write(f"... and {len(results['processed']) - 5} more")
                                
                                if results['failed']:
                                    st.write("❌ **Failed to process:**")
                                    for doc in results['failed'][:3]:  # Show first 3 errors
                                        st.write(f"- {doc['name']}: {doc['error']}")
                            else:
                                st.error(process_msg)
                    else:
                        st.error(msg)
        
        # System status
        st.header("📊 System Status")
        if st.session_state.rag_manager.initialized:
            st.success("✅ System Initialized")
            st.info(f"📂 Project: {st.session_state.rag_manager.project_id}")
            st.info(f"🌍 Location: {st.session_state.rag_manager.location}")
            st.info(f"🪣 Bucket: {st.session_state.rag_manager.bucket_name}")
            if st.session_state.processing_complete:
                st.success("✅ Documents Processed")
        else:
            st.warning("⚠️ System Not Initialized")
    
    # Main content - Query interface
    if not st.session_state.rag_manager.initialized:
        st.info("👈 Please initialize the system and process documents using the sidebar.")
        return
    
    if not st.session_state.processing_complete:
        st.warning("⚠️ Documents not yet processed. Please complete initialization first.")
        return
    
    # Query section
    st.markdown("""
    <div class="query-box">
        <h2>🔍 Query Your Documents</h2>
        <p>Ask questions about the processed documents from your knowledge base.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Query input
    query = st.text_area(
        "Enter your question:",
        placeholder="Ask anything about your documents...",
        height=100,
        help="Ask specific questions about the content in your document collection"
    )
    
    # Advanced settings in expander
    with st.expander("🎯 Advanced Query Settings"):
        # System prompt section
        st.subheader("System Prompt")
        
        # Preset prompts
        col1, col2 = st.columns([3, 1])
        with col1:
            preset_prompts = {
                "Default": "",
                "Analytical Expert": "You are an analytical expert. Provide detailed, structured responses with clear reasoning and evidence from the documents. Include specific examples and data points when available.",
                "Executive Summary": "You are an executive assistant. Provide concise, high-level summaries focusing on key business insights, decisions, and strategic implications from the documents.",
                "Technical Specialist": "You are a technical specialist. Focus on technical details, specifications, processes, and provide in-depth technical explanations based on the document content.",
                "Project Manager": "You are a project management expert. Focus on timelines, deliverables, risks, resources, and project-related information from the documents.",
                "Financial Analyst": "You are a financial analyst. Focus on costs, budgets, financial implications, ROI, and economic factors mentioned in the documents.",
                "Compliance Officer": "You are a compliance expert. Focus on regulations, standards, requirements, and compliance-related information from the documents."
            }
            
            selected_preset = st.selectbox(
                "Choose a preset system prompt:",
                options=list(preset_prompts.keys()),
                help="Select a preset for specialized responses"
            )
        
        with col2:
            if st.button("📝 Apply Preset"):
                st.session_state.system_prompt = preset_prompts[selected_preset]
                st.rerun()
        
        # Initialize system prompt in session state
        if 'system_prompt' not in st.session_state:
            st.session_state.system_prompt = ""
        
        # Custom system prompt input
        system_prompt = st.text_area(
            "Custom System Prompt:",
            value=st.session_state.system_prompt,
            height=100,
            help="Customize how the AI should respond to your queries"
        )
        
        # Query parameters
        col1, col2 = st.columns(2)
        with col1:
            top_k = st.slider("Number of documents to retrieve", 1, 10, 5, 
                            help="How many relevant document chunks to use for answering")
        
        with col2:
            if st.button("🔄 Reset Settings"):
                st.session_state.system_prompt = ""
                st.rerun()
    
    # Query execution
    if st.button("🔍 Search Documents", type="primary", disabled=not query.strip()):
        if query.strip():
            with st.spinner("Searching through your documents..."):
                success, response = st.session_state.rag_manager.query_documents(
                    query.strip(), 
                    top_k=top_k, 
                    system_prompt=system_prompt if system_prompt.strip() else None
                )
                
                if success:
                    st.markdown("### 📋 **Response:**")
                    st.markdown(response)
                    
                    # Add timestamp
                    st.markdown(f"*Query executed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
                else:
                    st.error(f"❌ {response}")
        else:
            st.warning("Please enter a question to search.")
    
    # Footer info
    st.markdown("---")
    st.markdown(f"📁 **Document Source:** `{DOCUMENTS_FOLDER}`")
    st.markdown("🤖 **Powered by:** Google Vertex AI with RAG")

if __name__ == "__main__":
    main() 