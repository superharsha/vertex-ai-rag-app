#!/usr/bin/env python3
"""
Streamlit frontend for Vertex AI RAG system
Enhanced with automatic bucket creation support
"""

import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="Vertex AI RAG System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #ff7f0e;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin-bottom: 1rem;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def get_api_status():
    """Get API status"""
    try:
        response = requests.get(f"{API_BASE_URL}/status")
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def get_documents():
    """Get list of documents"""
    try:
        response = requests.get(f"{API_BASE_URL}/documents")
        if response.status_code == 200:
            return response.json().get("documents", [])
        return []
    except:
        return []

def get_corpus_info():
    """Get corpus information"""
    try:
        response = requests.get(f"{API_BASE_URL}/corpus")
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def create_bucket():
    """Create GCS bucket manually"""
    try:
        response = requests.get(f"{API_BASE_URL}/bucket/create")
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"detail": str(e)}

def upload_files(files, description, chunk_size, chunk_overlap):
    """Upload files to the API"""
    try:
        files_data = []
        for file in files:
            files_data.append(('files', (file.name, file.getvalue(), file.type)))
        
        data = {
            'description': description,
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap
        }
        
        response = requests.post(f"{API_BASE_URL}/upload", files=files_data, data=data)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"detail": str(e)}

def query_documents(query, top_k, distance_threshold):
    """Query the documents"""
    try:
        data = {
            "query": query,
            "top_k": top_k,
            "distance_threshold": distance_threshold
        }
        response = requests.post(f"{API_BASE_URL}/query", json=data)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"detail": str(e)}

def clear_documents():
    """Clear all documents"""
    try:
        response = requests.post(f"{API_BASE_URL}/clear")
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"detail": str(e)}

# Main app
def main():
    # Header
    st.markdown('<h1 class="main-header">🤖 Vertex AI RAG System</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">Auto Bucket Creation • PDF/DOCX Support • Intelligent Querying</p>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("📊 System Status")
    
    # Get system status
    status = get_api_status()
    if status:
        st.sidebar.success("✅ API Connected")
        
        # Display metrics
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Documents", status.get("total_documents", 0))
        with col2:
            st.metric("Bucket", "✅" if status.get("bucket_exists") else "❌")
        
        # System info
        st.sidebar.subheader("🔧 Configuration")
        st.sidebar.text(f"Project: {status.get('project_id', 'N/A')}")
        st.sidebar.text(f"Location: {status.get('location', 'N/A')}")
        st.sidebar.text(f"Bucket: {status.get('bucket', 'N/A')}")
        
        # Bucket status
        if status.get("bucket_exists"):
            st.sidebar.success("🪣 Bucket Ready")
        else:
            st.sidebar.warning("🪣 Bucket Missing")
            if st.sidebar.button("Create Bucket"):
                with st.spinner("Creating bucket..."):
                    success, result = create_bucket()
                    if success:
                        st.sidebar.success(f"✅ {result.get('message', 'Bucket created')}")
                        st.rerun()
                    else:
                        st.sidebar.error(f"❌ {result.get('detail', 'Failed to create bucket')}")
        
        # Corpus info
        if status.get("active_corpus"):
            st.sidebar.info(f"📚 Active Corpus")
            corpus_info = get_corpus_info()
            if corpus_info and "name" in corpus_info:
                st.sidebar.text(f"Name: {corpus_info['display_name']}")
                st.sidebar.text(f"Documents: {corpus_info['document_count']}")
        else:
            st.sidebar.warning("📚 No Active Corpus")
    else:
        st.sidebar.error("❌ API Disconnected")
        st.sidebar.warning("Please ensure the FastAPI backend is running on port 8000")
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Documents", "🔍 Query Documents", "📋 Document Library", "⚙️ Settings"])
    
    # Upload Tab
    with tab1:
        st.markdown('<h2 class="sub-header">📤 Upload Documents</h2>', unsafe_allow_html=True)
        
        if not status:
            st.error("❌ Cannot upload documents. API is not available.")
            return
        
        # Check configuration
        if status.get("project_id") == "Not configured" or status.get("bucket") == "Not configured":
            st.markdown("""
            <div class="error-box">
                <h4>⚠️ Configuration Required</h4>
                <p>Please configure your Google Cloud settings:</p>
                <ul>
                    <li>Set <code>PROJECT_ID</code> environment variable</li>
                    <li>Set <code>GCS_BUCKET</code> environment variable (optional - will auto-generate)</li>
                    <li>Ensure Google Cloud credentials are configured</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # Bucket status display
        if status.get("bucket_exists"):
            st.markdown(f"""
            <div class="success-box">
                <h4>🪣 Storage Ready</h4>
                <p>GCS Bucket: <code>{status.get('bucket')}</code></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="warning-box">
                <h4>🪣 Bucket Will Be Created</h4>
                <p>GCS Bucket <code>{status.get('bucket')}</code> will be created automatically upon first upload.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # File upload
        uploaded_files = st.file_uploader(
            "Choose PDF, DOCX, TXT, or MD files",
            type=['pdf', 'docx', 'txt', 'md'],
            accept_multiple_files=True,
            help="Focus on PDF and DOCX files for best RAG performance"
        )
        
        if uploaded_files:
            # Display file preview
            st.subheader("📋 Selected Files")
            file_data = []
            total_size = 0
            for file in uploaded_files:
                file_size = len(file.getvalue())
                total_size += file_size
                file_type = file.name.split('.')[-1].upper()
                file_data.append({
                    "Filename": file.name,
                    "Type": file_type,
                    "Size (KB)": round(file_size / 1024, 2)
                })
            
            df = pd.DataFrame(file_data)
            st.dataframe(df, use_container_width=True)
            st.caption(f"Total size: {round(total_size / 1024, 2)} KB")
        
        # Upload settings
        st.subheader("⚙️ Processing Settings")
        col1, col2 = st.columns(2)
        with col1:
            description = st.text_input("Description (optional)", placeholder="Describe your documents...")
            chunk_size = st.slider("Chunk Size", 128, 2048, 512, help="Size of text chunks for processing")
        with col2:
            chunk_overlap = st.slider("Chunk Overlap", 0, 200, 100, help="Overlap between consecutive chunks")
        
        # Upload button
        if uploaded_files and st.button("🚀 Upload Documents", type="primary"):
            with st.spinner("Uploading and processing documents..."):
                success, result = upload_files(uploaded_files, description, chunk_size, chunk_overlap)
                
                if success:
                    # Display success message
                    bucket_status = "🆕 Created new bucket" if result.get('bucket_created') else "📁 Used existing bucket"
                    corpus_status = "✅ Added to corpus" if result.get('corpus_updated') else "⚠️ Corpus update failed"
                    
                    st.markdown(f"""
                    <div class="success-box">
                        <h4>✅ Upload Successful!</h4>
                        <p>{result.get('message', 'Documents uploaded successfully')}</p>
                        <p>{bucket_status} • {corpus_status}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display uploaded files details
                    if result.get('uploaded_files'):
                        st.subheader("📄 Uploaded Files")
                        upload_data = []
                        for file_info in result['uploaded_files']:
                            upload_data.append({
                                "Filename": file_info.get('filename', 'Unknown'),
                                "Type": file_info.get('file_type', 'Unknown'),
                                "Status": "✅ Success" if file_info.get('corpus_updated') else "⚠️ Failed",
                                "GCS Path": file_info.get('gcs_path', 'Unknown')
                            })
                        
                        df_upload = pd.DataFrame(upload_data)
                        st.dataframe(df_upload, use_container_width=True)
                    
                    st.rerun()
                else:
                    st.markdown(f"""
                    <div class="error-box">
                        <h4>❌ Upload Failed</h4>
                        <p>{result.get('detail', 'Unknown error occurred')}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Query Tab
    with tab2:
        st.markdown('<h2 class="sub-header">🔍 Query Documents</h2>', unsafe_allow_html=True)
        
        if not status:
            st.error("❌ Cannot query documents. API is not available.")
            return
        
        # Check if documents are uploaded
        documents = get_documents()
        if not documents:
            st.markdown("""
            <div class="info-box">
                <h4>📚 No Documents Available</h4>
                <p>Please upload PDF or DOCX documents first in the "Upload Documents" tab to start querying.</p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Document stats
        pdf_count = len([d for d in documents if d.get('file_type', '').lower() == 'pdf'])
        docx_count = len([d for d in documents if d.get('file_type', '').lower() == 'docx'])
        other_count = len(documents) - pdf_count - docx_count
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Documents", len(documents))
        with col2:
            st.metric("PDF Files", pdf_count)
        with col3:
            st.metric("DOCX Files", docx_count)
        with col4:
            st.metric("Other Files", other_count)
        
        # Query input
        query = st.text_area(
            "Enter your question:",
            placeholder="What would you like to know about your documents?",
            height=100
        )
        
        # Query settings
        col1, col2 = st.columns(2)
        with col1:
            top_k = st.slider("Number of Results", 1, 10, 3, help="Number of relevant chunks to retrieve")
        with col2:
            distance_threshold = st.slider("Relevance Threshold", 0.0, 1.0, 0.5, help="Minimum relevance score")
        
        # Query button
        if query and st.button("🔍 Search", type="primary"):
            with st.spinner("Searching documents..."):
                success, result = query_documents(query, top_k, distance_threshold)
                
                if success:
                    st.markdown(f"""
                    <div class="success-box">
                        <h4>🎯 Query Results</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display answer
                    st.markdown("### 💡 Answer")
                    answer = result.get("answer", "No answer generated")
                    st.markdown(answer)
                    
                    # Display retrieval results
                    if result.get("retrieval_results"):
                        st.markdown("### 📄 Retrieved Context")
                        for i, context in enumerate(result["retrieval_results"], 1):
                            with st.expander(f"Context {i} - {context.get('source', 'Unknown Source')}"):
                                st.markdown(context.get("text", "No text available"))
                                st.caption(f"Relevance: {context.get('relevance_score', 'N/A')}")
                    
                    # Display corpus info
                    st.caption(f"Corpus used: {result.get('corpus_used', 'Unknown')}")
                    
                else:
                    st.markdown(f"""
                    <div class="error-box">
                        <h4>❌ Query Failed</h4>
                        <p>{result.get('detail', 'Unknown error occurred')}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Document Library Tab
    with tab3:
        st.markdown('<h2 class="sub-header">📋 Document Library</h2>', unsafe_allow_html=True)
        
        documents = get_documents()
        
        if not documents:
            st.markdown("""
            <div class="info-box">
                <h4>📚 No Documents Uploaded</h4>
                <p>Your document library is empty. Upload some PDF or DOCX documents to get started!</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Documents table
            df_data = []
            for doc in documents:
                df_data.append({
                    "Filename": doc.get("filename", "Unknown"),
                    "Type": doc.get("file_type", "Unknown"),
                    "Size (KB)": round(doc.get("file_size", 0) / 1024, 2),
                    "Upload Time": doc.get("upload_time", "Unknown"),
                    "Status": "✅ In Corpus" if doc.get("corpus_updated") else "⚠️ Not Indexed",
                    "Description": doc.get("description", "No description")
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                total_size = sum(doc.get("file_size", 0) for doc in documents)
                st.metric("Total Size", f"{round(total_size / 1024 / 1024, 2)} MB")
            with col2:
                indexed_count = len([d for d in documents if d.get("corpus_updated")])
                st.metric("Indexed Documents", f"{indexed_count}/{len(documents)}")
            with col3:
                avg_size = total_size / len(documents) if documents else 0
                st.metric("Average Size", f"{round(avg_size / 1024, 2)} KB")
            
            # Clear documents button
            st.subheader("🗑️ Cleanup")
            if st.button("Clear All Documents", type="secondary"):
                if st.button("⚠️ Confirm Clear All"):
                    with st.spinner("Clearing documents..."):
                        success, result = clear_documents()
                        if success:
                            st.success("✅ All documents cleared successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to clear documents: {result.get('detail', 'Unknown error')}")
    
    # Settings Tab
    with tab4:
        st.markdown('<h2 class="sub-header">⚙️ Settings</h2>', unsafe_allow_html=True)
        
        # API Configuration
        st.markdown("### 🔧 API Configuration")
        st.code(f"API Base URL: {API_BASE_URL}")
        
        if status:
            st.markdown("### 📊 System Information")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                **Project Configuration:**
                - Project ID: `{status.get('project_id', 'N/A')}`
                - Location: `{status.get('location', 'N/A')}`
                - Status: `{status.get('status', 'N/A')}`
                """)
            
            with col2:
                st.markdown(f"""
                **Storage:**
                - GCS Bucket: `{status.get('bucket', 'N/A')}`
                - Bucket Exists: `{status.get('bucket_exists', False)}`
                - Total Documents: `{status.get('total_documents', 0)}`
                - Active Corpus: `{status.get('active_corpus', 'None')}`
                """)
        
        # Supported File Types
        st.markdown("### 📄 Supported File Types")
        st.markdown("""
        | File Type | Extension | Best For |
        |-----------|-----------|----------|
        | 📄 PDF | `.pdf` | Research papers, reports, manuals |
        | 📝 Word Document | `.docx` | Business documents, proposals |
        | 📋 Text File | `.txt` | Plain text content |
        | 📓 Markdown | `.md` | Documentation, notes |
        """)
        
        # Environment Variables Guide
        st.markdown("### 🌍 Environment Variables")
        st.markdown("""
        To use this system, configure these environment variables:
        
        ```bash
        # Required
        export PROJECT_ID="your-gcp-project-id"
        
        # Optional (will auto-generate if not set)
        export GCS_BUCKET="your-bucket-name"
        
        # Additional settings
        export LOCATION="us-central1"
        export GEN_MODEL="gemini-2.0-flash-001"
        
        # Authentication
        export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
        ```
        """)
        
        # Features
        st.markdown("### ✨ Key Features")
        st.markdown("""
        - **🪣 Auto Bucket Creation**: Automatically creates GCS buckets if they don't exist
        - **📄 Multi-Format Support**: PDF, DOCX, TXT, and Markdown files
        - **🤖 Intelligent RAG**: Uses Google Vertex AI for smart document retrieval
        - **⚡ Real-time Processing**: Asynchronous document processing
        - **📊 Comprehensive Monitoring**: Detailed status and logging
        """)

if __name__ == "__main__":
    main() 