#!/usr/bin/env python3
"""
Test script for Vertex AI RAG System
Demonstrates document upload and querying capabilities
"""

import requests
import json
import time
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"

def test_api_status():
    """Test API status"""
    print("🔍 Testing API Status...")
    try:
        response = requests.get(f"{API_BASE_URL}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ API Status: {status['status']}")
            print(f"📊 Project ID: {status['project_id']}")
            print(f"📍 Location: {status['location']}")
            print(f"🪣 Bucket: {status['bucket']}")
            print(f"🪣 Bucket Exists: {'Yes' if status['bucket_exists'] else 'No'}")
            print(f"📄 Total Documents: {status['total_documents']}")
            return True
        else:
            print(f"❌ API Status Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Connection Error: {e}")
        return False

def create_test_document():
    """Create a test document for upload"""
    print("\n📄 Creating test document...")
    
    test_content = """
Vertex AI RAG Test Document

Introduction
This is a test document for the Vertex AI RAG (Retrieval-Augmented Generation) system.
The system supports multiple document formats including PDF, DOCX, TXT, and Markdown.

Key Features
- Automatic Bucket Creation: The system automatically creates Google Cloud Storage buckets
- Multi-format Support: Supports PDF, DOCX, TXT, and Markdown files
- Intelligent Retrieval: Uses Google Vertex AI for smart document retrieval
- Real-time Processing: Processes documents asynchronously

Benefits
1. Easy to use interface
2. Scalable architecture
3. Google Cloud integration
4. Advanced AI capabilities

Use Cases
- Document Q&A systems
- Knowledge management
- Research assistance
- Content analysis

Technical Details
The system uses Google Vertex AI's RAG API to:
- Create and manage document corpora
- Import documents with configurable chunking
- Perform semantic search across documents
- Generate context-aware responses

This document contains information about artificial intelligence, machine learning,
and document processing capabilities.
"""
    
    test_file = Path("test_vertex_rag_document.txt")
    test_file.write_text(test_content)
    print(f"✅ Created test document: {test_file}")
    return test_file

def test_document_upload(file_path):
    """Test document upload"""
    print(f"\n📤 Testing document upload: {file_path}")
    
    try:
        with open(file_path, 'rb') as f:
            # Don't specify content type to avoid conflicts
            files = {'files': (file_path.name, f)}
            data = {
                'description': 'Test document for Vertex AI RAG system',
                'chunk_size': 512,
                'chunk_overlap': 100
            }
            
            response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload successful: {result['message']}")
                print(f"🪣 Bucket created: {'Yes' if result['bucket_created'] else 'No'}")
                print(f"📚 Corpus updated: {'Yes' if result['corpus_updated'] else 'No'}")
                
                if result.get('uploaded_files'):
                    for file_info in result['uploaded_files']:
                        print(f"📄 File: {file_info['filename']}")
                        print(f"   Type: {file_info['file_type']}")
                        print(f"   Status: {'✅ Success' if file_info['corpus_updated'] else '❌ Failed'}")
                
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def test_document_query(query):
    """Test document querying"""
    print(f"\n🔍 Testing query: '{query}'")
    
    try:
        data = {
            "query": query,
            "top_k": 3,
            "distance_threshold": 0.5
        }
        
        response = requests.post(f"{API_BASE_URL}/query", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Query successful!")
            print(f"\n💡 Answer:")
            print(f"{result['answer']}")
            
            if result.get('retrieval_results'):
                print(f"\n📄 Retrieved contexts ({len(result['retrieval_results'])}):")
                for i, context in enumerate(result['retrieval_results'], 1):
                    print(f"\n{i}. {context.get('source', 'Unknown Source')}")
                    text = context.get('text', 'No text')
                    print(f"   {text[:150]}..." if len(text) > 150 else f"   {text}")
            
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Query error: {e}")
        return False

def test_list_documents():
    """Test listing documents"""
    print("\n📋 Testing document listing...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/documents")
        
        if response.status_code == 200:
            result = response.json()
            documents = result.get('documents', [])
            print(f"✅ Found {len(documents)} documents")
            
            for doc in documents:
                print(f"📄 {doc.get('filename', 'Unknown')}")
                print(f"   Type: {doc.get('file_type', 'Unknown')}")
                print(f"   Size: {doc.get('file_size', 0)} bytes")
                print(f"   Status: {'✅ Indexed' if doc.get('corpus_updated') else '⚠️ Not indexed'}")
            
            return True
        else:
            print(f"❌ List failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ List error: {e}")
        return False

def test_corpus_info():
    """Test corpus information"""
    print("\n📚 Testing corpus information...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/corpus")
        
        if response.status_code == 200:
            result = response.json()
            if 'name' in result:
                print(f"✅ Corpus active:")
                print(f"   Name: {result['display_name']}")
                print(f"   Documents: {result['document_count']}")
                print(f"   Created: {result['created_time']}")
            else:
                print(f"ℹ️ No active corpus")
            return True
        else:
            print(f"❌ Corpus info failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Corpus info error: {e}")
        return False

def main():
    """Main test function"""
    print("🤖 Vertex AI RAG System Test")
    print("=" * 40)
    
    # Test API status
    if not test_api_status():
        print("❌ API not available. Please start the system first.")
        return
    
    # Wait a moment for system to be ready
    print("\n⏳ Waiting for system to be ready...")
    time.sleep(2)
    
    # Create and upload test document
    test_file = create_test_document()
    
    if test_document_upload(test_file):
        # Wait for document processing
        print("\n⏳ Waiting for document processing...")
        time.sleep(5)
        
        # Test queries
        test_queries = [
            "What are the key features of the system?",
            "What file formats are supported?",
            "How does the RAG system work?",
            "What are the benefits of using this system?"
        ]
        
        for query in test_queries:
            if test_document_query(query):
                time.sleep(2)  # Brief pause between queries
    
    # Test other endpoints
    test_list_documents()
    test_corpus_info()
    
    # Cleanup
    try:
        test_file.unlink()
        print(f"\n🧹 Cleaned up test file: {test_file}")
    except:
        pass
    
    print("\n✅ Test completed!")
    print("\n💡 Access the web interface at: http://localhost:8501")
    print("💡 API documentation at: http://localhost:8000/docs")

if __name__ == "__main__":
    main() 