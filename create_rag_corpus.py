#!/usr/bin/env python3
"""
Create RAG Corpus following Google Cloud documentation exactly
https://cloud.google.com/vertex-ai/generative-ai/docs/rag/get-started-python#run_vertex_ai_rag_engine
"""

import sys
import os

# Add homebrew site-packages to path
sys.path.insert(0, '/opt/homebrew/lib/python3.11/site-packages')

# Now import the required modules
import glob
import time
from datetime import datetime
import vertexai
from vertexai import rag
from google.cloud import storage

# Configuration
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "vpc-host-nonprod-kk186-dr143")
LOCATION = "us-central1"
DISPLAY_NAME = "document-knowledge-base"
DOCUMENTS_FOLDER = "/Users/sr/Downloads/All Files"
BUCKET_NAME = f"{PROJECT_ID}-rag-documents"
CORPUS_FILE = "corpus_name.txt"

def setup_storage_and_upload():
    """Upload files to Google Cloud Storage"""
    from google.cloud import storage
    
    print("📦 Setting up Google Cloud Storage...")
    
    # Initialize storage client
    client = storage.Client(project=PROJECT_ID)
    
    # Create bucket if it doesn't exist
    try:
        bucket = client.get_bucket(BUCKET_NAME)
        print(f"✅ Bucket exists: {BUCKET_NAME}")
    except:
        bucket = client.create_bucket(BUCKET_NAME, location=LOCATION)
        print(f"✅ Created bucket: {BUCKET_NAME}")
    
    # Upload files
    print("📤 Uploading files to bucket...")
    paths = []
    
    for filename in os.listdir(DOCUMENTS_FOLDER):
        if filename.lower().endswith(('.pdf', '.docx', '.txt', '.md')):
            local_path = os.path.join(DOCUMENTS_FOLDER, filename)
            blob_name = f"documents/{filename}"
            blob = bucket.blob(blob_name)
            
            print(f"  Uploading: {filename}")
            blob.upload_from_filename(local_path)
            
            gcs_uri = f"gs://{BUCKET_NAME}/{blob_name}"
            paths.append(gcs_uri)
    
    print(f"✅ Uploaded {len(paths)} files")
    return paths

def create_rag_corpus(paths):
    """Create RAG Corpus following Google documentation exactly"""
    
    print("🚀 Initializing Vertex AI...")
    # Initialize Vertex AI API once per session
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    # Check if corpus file already exists
    if os.path.exists(CORPUS_FILE):
        with open(CORPUS_FILE, "r") as f:
            existing_corpus_name = f.read().strip()
        
        try:
            print(f"🔍 Checking existing corpus: {existing_corpus_name}")
            existing_corpus = rag.get_corpus(name=existing_corpus_name)
            print(f"✅ Found existing corpus, using it: {existing_corpus.name}")
            return existing_corpus
        except Exception as e:
            print(f"⚠️ Existing corpus not found or invalid: {str(e)}")
            print("🧠 Creating new RAG Corpus...")
    else:
        print("🧠 Creating RAG Corpus...")
    
    # Create RagCorpus with timestamp to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    corpus_display_name = f"{DISPLAY_NAME}_{timestamp}"
    
    # Configure embedding model, for example "text-embedding-005"
    embedding_model_config = rag.RagEmbeddingModelConfig(
        vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
            publisher_model="publishers/google/models/text-embedding-005"
        )
    )

    rag_corpus = rag.create_corpus(
        display_name=corpus_display_name,
        backend_config=rag.RagVectorDbConfig(
            rag_embedding_model_config=embedding_model_config
        ),
    )
    
    print(f"✅ Created corpus: {rag_corpus.name}")
    
    # Import Files to the RagCorpus in batches of 25 (Google Cloud limit)
    print("📥 Importing files to RAG Corpus...")
    batch_size = 25
    total_imported = 0
    
    for i in range(0, len(paths), batch_size):
        batch = paths[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(paths) + batch_size - 1) // batch_size
        
        print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} files)...")
        
        try:
            rag.import_files(
                rag_corpus.name,
                batch,
                # Optional
                transformation_config=rag.TransformationConfig(
                    chunking_config=rag.ChunkingConfig(
                        chunk_size=512,
                        chunk_overlap=100,
                    ),
                ),
                max_embedding_requests_per_min=1000,  # Optional
            )
            total_imported += len(batch)
            print(f"✅ Imported batch {batch_num}/{total_batches} successfully")
            
            # Add a small delay between batches to avoid rate limits
            if i + batch_size < len(paths):
                print("⏳ Waiting 5 seconds before next batch...")
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ Failed to import batch {batch_num}: {str(e)}")
            continue
    
    print(f"✅ Total files imported: {total_imported}/{len(paths)}")
    
    # Save corpus name for Streamlit app
    with open(CORPUS_FILE, "w") as f:
        f.write(rag_corpus.name)
    print(f"💾 Saved corpus name to: {CORPUS_FILE}")
    
    return rag_corpus

def test_retrieval(rag_corpus):
    """Test direct context retrieval"""
    print("🔍 Testing retrieval...")
    
    # Direct context retrieval
    rag_retrieval_config = rag.RagRetrievalConfig(
        top_k=3,  # Optional
        filter=rag.Filter(vector_distance_threshold=0.5),  # Optional
    )
    
    response = rag.retrieval_query(
        rag_resources=[
            rag.RagResource(
                rag_corpus=rag_corpus.name,
            )
        ],
        text="What are the key topics in these documents?",
        rag_retrieval_config=rag_retrieval_config,
    )
    
    print("📋 Test retrieval response:")
    print(response)
    
    return True

def main():
    """Main function"""
    print("🚀 Starting RAG Corpus Creation")
    print("="*50)
    
    # Check if documents folder exists
    if not os.path.exists(DOCUMENTS_FOLDER):
        print(f"❌ Documents folder not found: {DOCUMENTS_FOLDER}")
        return
    
    # Upload files to GCS
    paths = setup_storage_and_upload()
    
    if not paths:
        print("❌ No files found to process")
        return
    
    # Create RAG corpus and import files
    rag_corpus = create_rag_corpus(paths)
    
    # Test retrieval
    test_retrieval(rag_corpus)
    
    print("\n🎉 RAG Corpus Creation Complete!")
    print("="*50)
    print(f"📚 Corpus: {rag_corpus.name}")
    print(f"📁 Files processed: {len(paths)}")
    print(f"💾 Corpus saved to: {CORPUS_FILE}")
    print("\n🔍 Next step: Run your Streamlit app!")
    print("streamlit run streamlit_standalone.py")

if __name__ == "__main__":
    main() 