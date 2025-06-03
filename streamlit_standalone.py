#!/usr/bin/env python3
"""
Standalone Streamlit App for Vertex AI RAG System
Ready for Streamlit Cloud deployment
"""

import streamlit as st

# Page config - MUST be first Streamlit command
st.set_page_config(
    page_title="Vertex AI RAG System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

import os
import json
import uuid
import tempfile
from datetime import datetime
from typing import List, Dict, Any
import logging

# Google Cloud imports
try:
    import vertexai
    from vertexai import rag
    from vertexai.generative_models import GenerativeModel, Tool
    from google.cloud import storage
    from google.cloud.exceptions import NotFound, Conflict
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

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
</style>
""", unsafe_allow_html=True)

class VertexAIRAGManager:
    def __init__(self):
        self.project_id = None
        self.location = None
        self.bucket_name = None
        self.generation_model = None
        self.corpus = None
        self.storage_client = None
        self.initialized = False
    
    def initialize(self, project_id: str, location: str = "us-central1", 
                  generation_model: str = "gemini-2.0-flash-001"):
        """Initialize Vertex AI and GCS"""
        try:
            self.project_id = project_id
            self.location = location
            self.generation_model = generation_model
            self.bucket_name = f"{project_id}-vertex-rag-docs"
            
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
    
    def create_or_get_corpus(self, display_name: str = "streamlit-rag-corpus") -> tuple[bool, str]:
        """Create or get existing RAG corpus"""
        try:
            # Try to create a new corpus
            embedding_model_config = rag.RagEmbeddingModelConfig(
                vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                    publisher_model="publishers/google/models/text-embedding-005"
                )
            )
            
            self.corpus = rag.create_corpus(
                display_name=f"{display_name}-{uuid.uuid4().hex[:8]}",
                backend_config=rag.RagVectorDbConfig(
                    rag_embedding_model_config=embedding_model_config
                ),
            )
            return True, f"Created corpus: {self.corpus.name}"
        except Exception as e:
            return False, f"Failed to create corpus: {str(e)}"
    
    def upload_file_to_gcs(self, file_content, filename: str, content_type: str) -> tuple[bool, str]:
        """Upload file to GCS bucket"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob_name = f"{uuid.uuid4().hex}_{filename}"
            blob = bucket.blob(blob_name)
            
            # Upload file content
            blob.upload_from_string(file_content, content_type=content_type)
            
            gcs_uri = f"gs://{self.bucket_name}/{blob_name}"
            return True, gcs_uri
        except Exception as e:
            return False, f"Failed to upload file: {str(e)}"
    
    def import_document_to_corpus(self, gcs_uri: str) -> tuple[bool, str]:
        """Import document from GCS to RAG corpus"""
        try:
            rag.import_files(
                self.corpus.name,
                [gcs_uri],
                transformation_config=rag.TransformationConfig(
                    chunking_config=rag.ChunkingConfig(
                        chunk_size=512,
                        chunk_overlap=100,
                    ),
                ),
                max_embedding_requests_per_min=1000,
            )
            return True, f"Document imported successfully: {gcs_uri}"
        except Exception as e:
            return False, f"Failed to import document: {str(e)}"
    
    def query_documents(self, query: str, top_k: int = 3, system_prompt: str = None) -> tuple[bool, str]:
        """Query the RAG corpus with optional system prompt"""
        try:
            if not self.corpus:
                return False, "No corpus available. Please upload documents first."
            
            # Create RAG tool
            retrieval = rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[rag.RagResource(rag_corpus=self.corpus.name)],
                    rag_retrieval_config=rag.RagRetrievalConfig(
                        top_k=top_k,
                        filter=rag.Filter(vector_distance_threshold=0.5),
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
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
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
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            os.unlink(tmp_file.name)
            return text
    except Exception as e:
        return f"Error extracting DOCX text: {str(e)}"

def setup_google_credentials():
    """Setup Google Cloud credentials from Streamlit secrets or ADC"""
    try:
        if "gcp_service_account" in st.secrets:
            # Create credentials from Streamlit secrets (for cloud deployment)
            service_account_info = dict(st.secrets["gcp_service_account"])
            
            # Write to temporary file for Google Cloud SDK
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
                json.dump(service_account_info, tmp_file)
                tmp_file.flush()
                
                # Set environment variable
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = tmp_file.name
                return True, "Google Cloud credentials configured from secrets"
        else:
            # For local testing, check if Application Default Credentials are available
            try:
                # Try to initialize a storage client to test credentials
                from google.auth import default
                credentials, project = default()
                if credentials and project:
                    return True, f"Using Application Default Credentials for project: {project}"
                else:
                    return False, "No valid credentials found"
            except Exception as e:
                return False, f"Application Default Credentials not available. Please run: gcloud auth application-default login"
    except Exception as e:
        return False, f"Failed to setup credentials: {str(e)}"

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Vertex AI RAG System</h1>
        <p>Upload documents and query them using Google's Vertex AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if required libraries are available
    if not GOOGLE_CLOUD_AVAILABLE:
        st.error("⚠️ Google Cloud libraries not installed. Please install requirements.")
        st.stop()
    
    # Setup credentials
    creds_success, creds_msg = setup_google_credentials()
    if not creds_success:
        st.error(f"❌ {creds_msg}")
        st.info("Please configure Google Cloud service account in Streamlit secrets.")
        st.stop()
    
    # Initialize session state
    if 'rag_manager' not in st.session_state:
        st.session_state.rag_manager = VertexAIRAGManager()
        st.session_state.uploaded_files = []
        st.session_state.corpus_created = False
    
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
        
        # Initialize button
        if st.button("🚀 Initialize System", type="primary"):
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
                        bucket_success, bucket_msg = st.session_state.rag_manager.create_bucket_if_not_exists()
                        if bucket_success:
                            st.success(bucket_msg)
                        else:
                            st.error(bucket_msg)
                    else:
                        st.error(msg)
        
        # System status
        st.header("📊 System Status")
        if st.session_state.rag_manager.initialized:
            st.success("✅ System Initialized")
            st.info(f"📂 Project: {st.session_state.rag_manager.project_id}")
            st.info(f"🌍 Location: {st.session_state.rag_manager.location}")
            st.info(f"🪣 Bucket: {st.session_state.rag_manager.bucket_name}")
        else:
            st.warning("⚠️ System Not Initialized")
    
    # Main content
    if not st.session_state.rag_manager.initialized:
        st.info("👈 Please initialize the system using the sidebar configuration.")
        return
    
    # File upload section
    st.header("📁 Document Upload")
    
    uploaded_files = st.file_uploader(
        "Upload Documents (PDF, DOCX, TXT)",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        help="Upload one or more documents to add to the knowledge base"
    )
    
    if uploaded_files and st.button("📤 Upload Documents"):
        # Create corpus if not exists
        if not st.session_state.corpus_created:
            with st.spinner("Creating RAG corpus..."):
                corpus_success, corpus_msg = st.session_state.rag_manager.create_or_get_corpus()
                if corpus_success:
                    st.success(corpus_msg)
                    st.session_state.corpus_created = True
                else:
                    st.error(corpus_msg)
                    st.stop()
        
        # Process each file
        for uploaded_file in uploaded_files:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                file_content = uploaded_file.read()
                
                # Determine content type and extract text if needed
                if uploaded_file.type == "application/pdf":
                    if PDF_DOCX_AVAILABLE:
                        text_content = extract_text_from_pdf(file_content)
                        content_to_upload = text_content.encode('utf-8')
                        content_type = "text/plain"
                        filename = uploaded_file.name.replace('.pdf', '.txt')
                    else:
                        st.error("PDF processing not available. Please install PyPDF2.")
                        continue
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    if PDF_DOCX_AVAILABLE:
                        text_content = extract_text_from_docx(file_content)
                        content_to_upload = text_content.encode('utf-8')
                        content_type = "text/plain"
                        filename = uploaded_file.name.replace('.docx', '.txt')
                    else:
                        st.error("DOCX processing not available. Please install python-docx.")
                        continue
                else:
                    content_to_upload = file_content
                    content_type = "text/plain"
                    filename = uploaded_file.name
                
                # Upload to GCS
                upload_success, gcs_uri_or_error = st.session_state.rag_manager.upload_file_to_gcs(
                    content_to_upload, filename, content_type
                )
                
                if upload_success:
                    st.success(f"✅ Uploaded: {uploaded_file.name}")
                    
                    # Import to corpus
                    import_success, import_msg = st.session_state.rag_manager.import_document_to_corpus(gcs_uri_or_error)
                    if import_success:
                        st.success(f"✅ Imported to RAG corpus: {uploaded_file.name}")
                        st.session_state.uploaded_files.append({
                            'name': uploaded_file.name,
                            'gcs_uri': gcs_uri_or_error,
                            'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    else:
                        st.error(f"❌ {import_msg}")
                else:
                    st.error(f"❌ {gcs_uri_or_error}")
    
    # Query section
    st.header("🔍 Query Documents")
    
    if st.session_state.uploaded_files:
        # Query input
        query = st.text_area(
            "Enter your question:",
            placeholder="Ask anything about your uploaded documents...",
            height=100
        )
        
        # System prompt section
        st.subheader("🎯 System Prompt (Optional)")
        
        # Preset prompts
        col1, col2 = st.columns([2, 1])
        with col1:
            preset_prompts = {
                "Default": "",
                "Analytical": "You are an analytical assistant. Provide detailed, structured responses with clear reasoning and evidence from the documents.",
                "Concise": "You are a concise assistant. Provide brief, direct answers while staying accurate to the document content.",
                "Technical Expert": "You are a technical expert. Focus on technical details, specifications, and provide in-depth explanations.",
                "Summarizer": "You are a summarization expert. Extract and present key information in a well-organized summary format.",
                "Q&A Assistant": "You are a helpful Q&A assistant. Answer questions directly and cite specific sections from the documents when possible.",
                "Creative": "You are a creative assistant. Provide engaging, well-structured responses that make the information accessible and interesting."
            }
            
            selected_preset = st.selectbox(
                "Choose a preset system prompt:",
                options=list(preset_prompts.keys()),
                help="Select a preset or use 'Default' for no system prompt"
            )
        
        with col2:
            if st.button("📝 Use Preset", help="Apply the selected preset to the system prompt field"):
                st.session_state.system_prompt = preset_prompts[selected_preset]
                st.rerun()
        
        # Initialize system prompt in session state if not exists
        if 'system_prompt' not in st.session_state:
            st.session_state.system_prompt = ""
        
        # Custom system prompt input
        system_prompt = st.text_area(
            "Custom System Prompt:",
            value=st.session_state.system_prompt,
            placeholder="Enter your custom system prompt here, or use a preset above...",
            height=120,
            help="This prompt will guide how Gemini responds to your queries"
        )
        
        # Update session state when text area changes
        if system_prompt != st.session_state.system_prompt:
            st.session_state.system_prompt = system_prompt
        
        # Query configuration
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            top_k = st.slider("Number of relevant chunks", 1, 10, 3, help="How many document chunks to use for context")
        with col2:
            st.write("") # Spacer
        with col3:
            if st.button("🗑️ Clear Prompt", help="Clear the system prompt"):
                st.session_state.system_prompt = ""
                st.rerun()
        
        # Query button and results
        if st.button("🔍 Query Documents", type="primary", use_container_width=True):
            if query.strip():
                with st.spinner("🤔 Searching and generating response..."):
                    # Show what system prompt is being used
                    if system_prompt.strip():
                        st.info(f"🎯 **Using System Prompt:** {system_prompt[:100]}{'...' if len(system_prompt) > 100 else ''}")
                    else:
                        st.info("🎯 **Using:** Default Gemini behavior (no custom system prompt)")
                    
                    success, response = st.session_state.rag_manager.query_documents(query, top_k, system_prompt)
                    
                    if success:
                        st.subheader("📝 Response:")
                        st.markdown(response)
                        
                        # Show query details in expandable section
                        with st.expander("🔍 Query Details"):
                            st.write(f"**Question:** {query}")
                            st.write(f"**Chunks Used:** {top_k}")
                            st.write(f"**Model:** {st.session_state.rag_manager.generation_model}")
                            if system_prompt.strip():
                                st.write(f"**System Prompt:** {system_prompt}")
                            else:
                                st.write("**System Prompt:** None (default behavior)")
                    else:
                        st.error(f"❌ {response}")
            else:
                st.warning("Please enter a question.")
    else:
        st.info("Upload documents first to enable querying.")
    
    # Document library
    if st.session_state.uploaded_files:
        st.header("📚 Document Library")
        
        for i, file_info in enumerate(st.session_state.uploaded_files):
            with st.expander(f"📄 {file_info['name']}"):
                st.write(f"**Uploaded:** {file_info['uploaded_at']}")
                st.write(f"**GCS URI:** `{file_info['gcs_uri']}`")

if __name__ == "__main__":
    main() 