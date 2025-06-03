#!/usr/bin/env python3
"""
FastAPI backend for Vertex AI RAG system
Supports multiple file uploads (PDF, DOCX) and intelligent querying
Automatically creates GCS buckets and manages document storage
"""

import os
import uuid
import tempfile
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Google Cloud and Vertex AI imports
from google.cloud import storage
from google.cloud.exceptions import NotFound, Conflict
from dotenv import load_dotenv
from vertexai import rag
from vertexai.generative_models import GenerativeModel, Tool
import vertexai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1") 
GCS_BUCKET = os.getenv("GCS_BUCKET")
EMBEDDING_MODEL = "publishers/google/models/text-embedding-005"
GENERATION_MODEL = os.getenv("GEN_MODEL", "gemini-2.0-flash-001")

# Auto-generate bucket name if not provided
if not GCS_BUCKET and PROJECT_ID:
    GCS_BUCKET = f"{PROJECT_ID}-vertex-rag-docs"

# Initialize Vertex AI
if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location=LOCATION)

# Data models
class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_size: int
    upload_time: str
    gcs_path: str
    description: Optional[str] = None
    file_type: str

class CorpusInfo(BaseModel):
    name: str
    display_name: str
    created_time: str
    document_count: int

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3
    distance_threshold: Optional[float] = 0.5

class QueryResponse(BaseModel):
    query: str
    answer: str
    retrieval_results: List[Dict[str, Any]]
    corpus_used: str

class UploadResponse(BaseModel):
    message: str
    uploaded_files: List[Dict[str, Any]]
    bucket_created: bool
    corpus_updated: bool

class StatusResponse(BaseModel):
    status: str
    project_id: str
    location: str
    bucket: str
    bucket_exists: bool
    total_documents: int
    active_corpus: Optional[str] = None

# Storage
documents_store: List[Dict[str, Any]] = []
current_corpus: Optional[rag.RagCorpus] = None
corpus_info: Optional[Dict[str, Any]] = None

# FastAPI app
app = FastAPI(
    title="Vertex AI RAG API",
    description="Upload PDF/DOCX documents and query using Google Vertex AI RAG with automatic GCS bucket creation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions
def get_gcs_client():
    """Get GCS client"""
    return storage.Client(project=PROJECT_ID)

def create_bucket_if_not_exists(bucket_name: str) -> bool:
    """Create GCS bucket if it doesn't exist"""
    try:
        client = get_gcs_client()
        
        # Check if bucket exists
        try:
            bucket = client.get_bucket(bucket_name)
            print(f"✅ Bucket {bucket_name} already exists")
            return False  # Bucket already existed
        except NotFound:
            pass
        
        # Create bucket
        bucket = client.bucket(bucket_name)
        bucket = client.create_bucket(bucket, location=LOCATION)
        
        print(f"✅ Created bucket {bucket_name} in {LOCATION}")
        return True  # Bucket was created
        
    except Conflict:
        print(f"⚠️ Bucket {bucket_name} already exists (conflict)")
        return False
    except Exception as e:
        print(f"❌ Error creating bucket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create bucket: {str(e)}")

def check_bucket_exists(bucket_name: str) -> bool:
    """Check if GCS bucket exists"""
    try:
        client = get_gcs_client()
        client.get_bucket(bucket_name)
        return True
    except NotFound:
        return False
    except Exception:
        return False

async def upload_to_gcs(file: UploadFile, description: str = "Document for RAG system") -> str:
    """Upload file to Google Cloud Storage"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Generate blob name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"documents/{timestamp}_{file.filename}"
        
        # Upload to GCS using the simplest possible approach
        bucket = storage.Client(project=PROJECT_ID).bucket(GCS_BUCKET)
        blob = bucket.blob(blob_name)
        
        # Use upload_from_string with bytes - no metadata or content type
        blob.upload_from_string(file_content)
        
        logger.info(f"Successfully uploaded {file.filename} to gs://{GCS_BUCKET}/{blob_name}")
        return f"gs://{GCS_BUCKET}/{blob_name}"
        
    except Exception as e:
        logger.error(f"Failed to upload {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}")

def create_or_get_corpus(display_name: str = "rag_corpus") -> rag.RagCorpus:
    """Create a new RAG corpus or get existing one"""
    global current_corpus, corpus_info
    
    try:
        embedding_model_config = rag.RagEmbeddingModelConfig(
            vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                publisher_model=EMBEDDING_MODEL
            )
        )
        
        corpus_name = f"{display_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        corpus = rag.create_corpus(
            display_name=corpus_name,
            backend_config=rag.RagVectorDbConfig(
                rag_embedding_model_config=embedding_model_config
            ),
        )
        
        current_corpus = corpus
        corpus_info = {
            "name": corpus.name,
            "display_name": corpus_name,
            "created_time": datetime.now().isoformat(),
            "document_count": 0
        }
        
        print(f"✅ Created RAG corpus: {corpus.name}")
        return corpus
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create corpus: {str(e)}")

def import_document_to_corpus(corpus_name: str, gcs_path: str, chunk_size: int = 512, chunk_overlap: int = 100):
    """Import a document from GCS to the RAG corpus"""
    try:
        print(f"📄 Importing document to corpus: {gcs_path}")
        rag.import_files(
            corpus_name,
            [gcs_path],
            transformation_config=rag.TransformationConfig(
                chunking_config=rag.ChunkingConfig(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                ),
            ),
            max_embedding_requests_per_min=1000,
        )
        print(f"✅ Successfully imported {gcs_path}")
        return True
    except Exception as e:
        print(f"❌ Error importing document: {str(e)}")
        return False

def perform_rag_query(corpus_name: str, query: str, top_k: int = 3, distance_threshold: float = 0.5):
    """Perform RAG query on the corpus"""
    try:
        print(f"🔍 Performing RAG query: {query}")
        
        # Retrieval
        retrieval_config = rag.RagRetrievalConfig(
            top_k=top_k,
            filter=rag.Filter(vector_distance_threshold=distance_threshold),
        )
        
        retrieval_response = rag.retrieval_query(
            rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
            text=query,
            rag_retrieval_config=retrieval_config,
        )
        
        # Generation with RAG
        retrieval = rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
                rag_retrieval_config=rag.RagRetrievalConfig(
                    top_k=top_k,
                    filter=rag.Filter(vector_distance_threshold=distance_threshold),
                )
            ),
        )
        
        rag_tool = Tool.from_retrieval(retrieval=retrieval)
        model = GenerativeModel(
            model_name=GENERATION_MODEL,
            tools=[rag_tool]
        )
        
        generation_response = model.generate_content(query)
        
        # Extract retrieval contexts
        retrieval_results = []
        if hasattr(retrieval_response, 'contexts') and retrieval_response.contexts:
            for i, context in enumerate(retrieval_response.contexts.contexts):
                retrieval_results.append({
                    "text": str(context.text) if hasattr(context, 'text') else str(context),
                    "relevance_score": "N/A",  # Vertex AI doesn't expose scores directly
                    "source": context.source_uri if hasattr(context, 'source_uri') else "Unknown"
                })
        
        return {
            "answer": generation_response.text,
            "retrieval_results": retrieval_results
        }
        
    except Exception as e:
        print(f"❌ Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# API Endpoints
@app.get("/")
def root():
    return {
        "message": "Vertex AI RAG API with Auto Bucket Creation",
        "version": "1.0.0",
        "description": "Upload PDF/DOCX documents and query using Google Vertex AI RAG",
        "features": [
            "Automatic GCS bucket creation",
            "PDF and DOCX document support", 
            "Intelligent document retrieval",
            "RAG-enhanced generation"
        ]
    }

@app.get("/status", response_model=StatusResponse)
def get_status():
    bucket_exists = check_bucket_exists(GCS_BUCKET) if GCS_BUCKET else False
    
    return StatusResponse(
        status="active",
        project_id=PROJECT_ID or "Not configured",
        location=LOCATION,
        bucket=GCS_BUCKET or "Not configured",
        bucket_exists=bucket_exists,
        total_documents=len(documents_store),
        active_corpus=corpus_info["name"] if corpus_info else None
    )

@app.get("/documents")
def list_documents():
    return {"documents": documents_store, "total_count": len(documents_store)}

@app.get("/corpus")
def get_corpus_info():
    if not corpus_info:
        return {"message": "No active corpus"}
    return corpus_info

@app.post("/upload", response_model=UploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    description: str = Form("Documents for RAG system"),
    chunk_size: int = Form(1024),
    chunk_overlap: int = Form(200)
):
    """Upload documents to GCS and add to RAG corpus"""
    
    # Check if bucket exists, create if needed
    bucket_created = False
    if not check_bucket_exists(GCS_BUCKET):
        try:
            create_bucket_if_not_exists(GCS_BUCKET)
            bucket_created = True
            logger.info(f"Created bucket: {GCS_BUCKET}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create bucket: {str(e)}")
    
    # Ensure corpus exists
    if not current_corpus:
        try:
            create_or_get_corpus()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create corpus: {str(e)}")
    
    uploaded_files = []
    corpus_updated = False
    
    for file in files:
        # Validate file type
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.pdf', '.docx', '.txt', '.md']:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_ext}. Supported types: .pdf, .docx, .txt, .md"
            )
        
        # Read file content for size calculation
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail=f"File {file.filename} is empty")
        
        # Reset file position for upload
        await file.seek(0)
        
        # Upload to GCS
        try:
            gcs_path = await upload_to_gcs(file, description)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}")
        
        # Import to RAG corpus
        try:
            import_result = import_document_to_corpus(
                current_corpus.name, 
                gcs_path, 
                chunk_size, 
                chunk_overlap
            )
            corpus_updated = True
            
            doc_id = str(uuid.uuid4())
            file_info = {
                "id": doc_id,
                "filename": file.filename,
                "file_size": file_size,
                "file_type": file_ext[1:].upper(),  # Remove dot and uppercase
                "upload_time": datetime.now().isoformat(),
                "gcs_path": gcs_path,
                "corpus_updated": True
            }
            uploaded_files.append(file_info)
            
            # Store in documents store
            documents_store.append({
                "id": doc_id,
                "filename": file.filename,
                "file_size": file_size,
                "file_type": file_ext[1:].upper(),
                "upload_time": datetime.now().isoformat(),
                "gcs_path": gcs_path,
                "description": description,
                "corpus_updated": True
            })
            
            # Update corpus info
            if corpus_info:
                corpus_info["document_count"] += 1
            
            logger.info(f"Successfully imported {file.filename} to corpus")
            
        except Exception as e:
            logger.error(f"Failed to import {file.filename} to corpus: {str(e)}")
            # Still add to list but mark as not corpus updated
            doc_id = str(uuid.uuid4())
            file_info = {
                "id": doc_id,
                "filename": file.filename,
                "file_size": file_size,
                "file_type": file_ext[1:].upper(),  # Remove dot and uppercase
                "upload_time": datetime.now().isoformat(),
                "gcs_path": gcs_path,
                "corpus_updated": False,
                "error": str(e)
            }
            uploaded_files.append(file_info)
    
    return UploadResponse(
        message=f"Successfully processed {len(uploaded_files)} file(s)",
        uploaded_files=uploaded_files,
        bucket_created=bucket_created,
        corpus_updated=corpus_updated
    )

@app.post("/query", response_model=QueryResponse)
async def query_documents(query_request: QueryRequest):
    if not current_corpus:
        raise HTTPException(status_code=400, detail="No corpus available. Please upload documents first.")
    
    if not documents_store:
        raise HTTPException(status_code=400, detail="No documents uploaded yet")
    
    try:
        result = perform_rag_query(
            current_corpus.name,
            query_request.query,
            query_request.top_k,
            query_request.distance_threshold
        )
        
        return QueryResponse(
            query=query_request.query,
            answer=result["answer"],
            retrieval_results=result["retrieval_results"],
            corpus_used=current_corpus.name
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    global documents_store
    
    # Find and remove document
    doc_to_remove = None
    for i, doc in enumerate(documents_store):
        if doc["id"] == doc_id:
            doc_to_remove = documents_store.pop(i)
            break
    
    if not doc_to_remove:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # TODO: Remove from GCS and corpus (requires additional API calls)
    
    return {
        "message": "Document deleted successfully",
        "deleted_document": doc_to_remove["filename"]
    }

@app.post("/clear")
def clear_all_documents():
    global documents_store, current_corpus, corpus_info
    documents_store.clear()
    current_corpus = None
    corpus_info = None
    
    return {"message": "All documents cleared successfully"}

@app.get("/bucket/create")
def create_bucket_endpoint():
    """Manual endpoint to create bucket"""
    if not GCS_BUCKET:
        raise HTTPException(status_code=400, detail="GCS_BUCKET not configured")
    
    try:
        bucket_created = create_bucket_if_not_exists(GCS_BUCKET)
        return {
            "message": f"Bucket operation completed",
            "bucket_name": GCS_BUCKET,
            "created": bucket_created,
            "status": "created" if bucket_created else "already_exists"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Starting Vertex AI RAG API with Auto Bucket Creation")
    print("📋 Configuration:")
    print(f"  • Project ID: {PROJECT_ID}")
    print(f"  • Location: {LOCATION}")
    print(f"  • GCS Bucket: {GCS_BUCKET}")
    print(f"  • Generation Model: {GENERATION_MODEL}")
    print(f"  • Supported File Types: PDF, DOCX, TXT, MD")
    print()
    
    if not PROJECT_ID:
        print("⚠️  Warning: PROJECT_ID not set in environment")
    if not GCS_BUCKET:
        print("⚠️  Warning: GCS_BUCKET not set in environment")
    else:
        print(f"🪣 Will create bucket '{GCS_BUCKET}' if it doesn't exist")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    ) 