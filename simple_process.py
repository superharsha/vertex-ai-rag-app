#!/usr/bin/env python3
import os
import sys
import time
from datetime import datetime

# Add the path to find the modules
sys.path.insert(0, '/opt/homebrew/lib/python3.11/site-packages')

try:
    import vertexai
    from vertexai import rag
    from google.cloud import storage
    from google.oauth2 import service_account
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Constants
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1"
DOCUMENTS_FOLDER = "/Users/sr/Downloads/All Files"
CORPUS_DISPLAY_NAME = "Document-Knowledge-Base"
BUCKET_NAME = f"{PROJECT_ID}-rag-documents"
CORPUS_FILE = "corpus_name.txt"

def check_environment():
    """Check if environment is properly set up"""
    print("🔍 Checking environment...")
    
    if not PROJECT_ID:
        print("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
        return False
    
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        return False
    
    if not os.path.exists(creds_path):
        print(f"❌ Credentials file not found: {creds_path}")
        return False
    
    if not os.path.exists(DOCUMENTS_FOLDER):
        print(f"❌ Documents folder not found: {DOCUMENTS_FOLDER}")
        return False
    
    print(f"✅ Project ID: {PROJECT_ID}")
    print(f"✅ Credentials: {creds_path}")
    print(f"✅ Documents folder: {DOCUMENTS_FOLDER}")
    return True

def initialize_vertex_ai():
    """Initialize Vertex AI"""
    try:
        print("🚀 Initializing Vertex AI...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        print("✅ Vertex AI initialized")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize Vertex AI: {e}")
        return False

def setup_storage_bucket():
    """Create storage bucket if it doesn't exist"""
    try:
        print("🗄️ Setting up storage bucket...")
        client = storage.Client(project=PROJECT_ID)
        
        # Check if bucket exists
        try:
            bucket = client.get_bucket(BUCKET_NAME)
            print(f"✅ Bucket exists: {BUCKET_NAME}")
        except:
            # Create bucket
            bucket = client.create_bucket(BUCKET_NAME, location=LOCATION)
            print(f"✅ Created bucket: {BUCKET_NAME}")
        
        return bucket
    except Exception as e:
        print(f"❌ Failed to setup storage bucket: {e}")
        return None

def create_corpus():
    """Create RAG corpus"""
    try:
        print("📚 Creating RAG corpus...")
        
        # Create corpus
        corpus = rag.create_corpus(display_name=CORPUS_DISPLAY_NAME)
        print(f"✅ Created corpus: {corpus.name}")
        
        # Save corpus name to file
        with open(CORPUS_FILE, "w") as f:
            f.write(corpus.name)
        print(f"✅ Saved corpus name to {CORPUS_FILE}")
        
        return corpus
    except Exception as e:
        print(f"❌ Failed to create corpus: {e}")
        return None

def upload_files_to_bucket(bucket):
    """Upload files to storage bucket"""
    try:
        print("📤 Uploading files to bucket...")
        
        uploaded_files = []
        
        for filename in os.listdir(DOCUMENTS_FOLDER):
            if filename.lower().endswith(('.pdf', '.docx', '.doc', '.txt')):
                local_path = os.path.join(DOCUMENTS_FOLDER, filename)
                
                # Upload to bucket
                blob_name = f"documents/{filename}"
                blob = bucket.blob(blob_name)
                
                print(f"  Uploading: {filename}")
                blob.upload_from_filename(local_path)
                
                # Get GCS URI
                gcs_uri = f"gs://{BUCKET_NAME}/{blob_name}"
                uploaded_files.append(gcs_uri)
        
        print(f"✅ Uploaded {len(uploaded_files)} files")
        return uploaded_files
    except Exception as e:
        print(f"❌ Failed to upload files: {e}")
        return []

def import_files_to_corpus(corpus, file_uris):
    """Import files into the RAG corpus"""
    try:
        print("📥 Importing files into corpus...")
        
        batch_size = 5  # Process in smaller batches
        
        for i in range(0, len(file_uris), batch_size):
            batch = file_uris[i:i+batch_size]
            print(f"  Processing batch {i//batch_size + 1}: {len(batch)} files")
            
            # Import batch
            rag.import_files(
                corpus=corpus.name,
                paths=batch,
                request_metadata=[{"key": "source", "value": "batch_upload"}] * len(batch)
            )
            
            print(f"  ✅ Imported batch {i//batch_size + 1}")
            time.sleep(2)  # Brief pause between batches
        
        print(f"✅ Imported all {len(file_uris)} files into corpus")
        return True
    except Exception as e:
        print(f"❌ Failed to import files to corpus: {e}")
        return False

def main():
    """Main processing function"""
    print("🚀 Starting document processing...")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Initialize Vertex AI
    if not initialize_vertex_ai():
        sys.exit(1)
    
    # Setup storage bucket
    bucket = setup_storage_bucket()
    if not bucket:
        sys.exit(1)
    
    # Create corpus
    corpus = create_corpus()
    if not corpus:
        sys.exit(1)
    
    # Upload files to bucket
    file_uris = upload_files_to_bucket(bucket)
    if not file_uris:
        print("❌ No files to process")
        sys.exit(1)
    
    # Import files to corpus
    if not import_files_to_corpus(corpus, file_uris):
        sys.exit(1)
    
    print("\n🎉 Document processing completed successfully!")
    print(f"📚 Corpus: {corpus.name}")
    print(f"📁 Files processed: {len(file_uris)}")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n🔍 Next steps:")
    print("1. Run your Streamlit app: streamlit run streamlit_standalone.py")
    print("2. The app will automatically load the created corpus")
    print("3. Start querying your documents!")

if __name__ == "__main__":
    main() 