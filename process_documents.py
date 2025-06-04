#!/usr/bin/env python3
"""
Document Processing Script for Vertex AI RAG
Processes all documents and creates a corpus for querying.
Run this once to build the knowledge base.
"""

import os
import glob
import uuid
import tempfile
from datetime import datetime

# Google Cloud imports
import vertexai
from vertexai import rag
from google.cloud import storage

# Document processing imports
try:
    import PyPDF2
    import docx
    PDF_DOCX_AVAILABLE = True
except ImportError:
    PDF_DOCX_AVAILABLE = False
    print("⚠️  PDF/DOCX processing not available. Install: pip install PyPDF2 python-docx")

# Configuration
DOCUMENTS_FOLDER = "/Users/sr/Downloads/All Files"
PROJECT_ID = "vpc-host-nonprod-kk186-dr143"
LOCATION = "us-central1"
CORPUS_NAME = "knowledge-base-production"
BUCKET_NAME = f"{PROJECT_ID}-knowledge-base-docs"

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

def setup_google_cloud():
    """Initialize Google Cloud services"""
    print("🔧 Initializing Google Cloud...")
    
    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    # Initialize Storage client
    storage_client = storage.Client(project=PROJECT_ID)
    
    return storage_client

def create_bucket(storage_client):
    """Create GCS bucket if it doesn't exist"""
    print(f"📦 Setting up storage bucket: {BUCKET_NAME}")
    
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        if not bucket.exists():
            bucket = storage_client.create_bucket(BUCKET_NAME, location=LOCATION)
            print(f"✅ Created bucket: {BUCKET_NAME}")
        else:
            print(f"✅ Bucket already exists: {BUCKET_NAME}")
        return bucket
    except Exception as e:
        print(f"❌ Failed to create bucket: {str(e)}")
        return None

def create_corpus():
    """Create RAG corpus"""
    print(f"🧠 Creating RAG corpus: {CORPUS_NAME}")
    
    try:
        corpus_display_name = f"{CORPUS_NAME}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        corpus = rag.create_corpus(display_name=corpus_display_name)
        print(f"✅ Created corpus: {corpus.name}")
        
        # Save corpus name to file for Streamlit app to use
        with open("corpus_name.txt", "w") as f:
            f.write(corpus.name)
        print(f"💾 Saved corpus name to: corpus_name.txt")
        
        return corpus
    except Exception as e:
        print(f"❌ Failed to create corpus: {str(e)}")
        return None

def get_all_files():
    """Get all supported files from documents folder"""
    print(f"📁 Scanning folder: {DOCUMENTS_FOLDER}")
    
    if not os.path.exists(DOCUMENTS_FOLDER):
        print(f"❌ Folder not found: {DOCUMENTS_FOLDER}")
        return []
    
    file_patterns = ['*.pdf', '*.docx', '*.txt', '*.md']
    all_files = []
    for pattern in file_patterns:
        files = glob.glob(os.path.join(DOCUMENTS_FOLDER, pattern))
        all_files.extend(files)
    
    print(f"📄 Found {len(all_files)} files to process")
    for i, file_path in enumerate(all_files[:10], 1):  # Show first 10
        print(f"   {i}. {os.path.basename(file_path)}")
    if len(all_files) > 10:
        print(f"   ... and {len(all_files) - 10} more files")
    
    return all_files

def process_file(file_path, bucket):
    """Process a single file and upload to GCS"""
    filename = os.path.basename(file_path)
    print(f"📝 Processing: {filename}")
    
    try:
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
                print(f"   ⚠️  Skipping PDF (PyPDF2 not available): {filename}")
                return False, f"PDF processing not available"
                
        elif file_path.lower().endswith('.docx'):
            if PDF_DOCX_AVAILABLE:
                with open(file_path, 'rb') as f:
                    text_content = extract_text_from_docx(f.read())
                blob.upload_from_string(text_content.encode('utf-8'), content_type="text/plain")
                blob_name = blob_name.replace('.docx', '.txt')
            else:
                print(f"   ⚠️  Skipping DOCX (python-docx not available): {filename}")
                return False, f"DOCX processing not available"
                
        elif file_path.lower().endswith(('.txt', '.md')):
            blob.upload_from_filename(file_path, content_type="text/plain")
            
        else:
            print(f"   ⚠️  Unsupported file type: {filename}")
            return False, f"Unsupported file type"
        
        gcs_uri = f"gs://{bucket.name}/{blob_name}"
        print(f"   ✅ Uploaded to: {gcs_uri}")
        return True, gcs_uri
        
    except Exception as e:
        print(f"   ❌ Error processing {filename}: {str(e)}")
        return False, str(e)

def import_to_corpus(corpus, gcs_uri, filename):
    """Import document from GCS to RAG corpus"""
    print(f"🔄 Importing to corpus: {filename}")
    
    try:
        rag.import_files(
            corpus.name,
            [gcs_uri],
            max_embedding_requests_per_min=100,
        )
        print(f"   ✅ Successfully imported: {filename}")
        return True
    except Exception as e:
        print(f"   ❌ Failed to import {filename}: {str(e)}")
        return False

def main():
    """Main processing function"""
    print("🚀 Starting Document Processing Pipeline")
    print("="*50)
    
    # Setup
    storage_client = setup_google_cloud()
    bucket = create_bucket(storage_client)
    if not bucket:
        return
    
    corpus = create_corpus()
    if not corpus:
        return
    
    # Get files
    all_files = get_all_files()
    if not all_files:
        print("❌ No files found to process")
        return
    
    # Process files
    print(f"\n📚 Processing {len(all_files)} documents...")
    print("="*50)
    
    processed_count = 0
    failed_files = []
    
    for i, file_path in enumerate(all_files, 1):
        filename = os.path.basename(file_path)
        print(f"\n[{i}/{len(all_files)}] {filename}")
        
        # Upload to GCS
        upload_success, gcs_uri_or_error = process_file(file_path, bucket)
        
        if upload_success:
            # Import to corpus
            import_success = import_to_corpus(corpus, gcs_uri_or_error, filename)
            if import_success:
                processed_count += 1
            else:
                failed_files.append(filename)
        else:
            failed_files.append(f"{filename}: {gcs_uri_or_error}")
    
    # Summary
    print("\n" + "="*50)
    print("🎉 PROCESSING COMPLETE!")
    print("="*50)
    print(f"✅ Successfully processed: {processed_count}/{len(all_files)} files")
    print(f"🏗️  Corpus created: {corpus.name}")
    print(f"📦 Storage bucket: {bucket.name}")
    
    if failed_files:
        print(f"\n❌ Failed files ({len(failed_files)}):")
        for failed_file in failed_files:
            print(f"   • {failed_file}")
    
    print(f"\n💾 Corpus name saved to: corpus_name.txt")
    print("🔍 Your Streamlit app can now query this knowledge base!")
    
    return corpus.name, processed_count, len(all_files)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Processing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc() 