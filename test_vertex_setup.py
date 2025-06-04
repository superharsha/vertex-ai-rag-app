#!/usr/bin/env python3

import os
import sys

def test_vertex_ai_setup():
    """Test basic Vertex AI setup"""
    print("🧪 Testing Vertex AI Setup")
    print("-" * 40)
    
    # Check environment variables
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    print(f"📋 Project ID: {project_id}")
    print(f"🔑 Credentials: {creds_path}")
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
        return False
        
    if not creds_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        return False
    
    # Test credentials file exists
    if not os.path.exists(os.path.expanduser(creds_path)):
        print(f"❌ Credentials file not found: {creds_path}")
        return False
    
    print("✅ Environment variables configured correctly")
    
    # Test imports
    try:
        print("🔄 Testing imports...")
        import vertexai
        print(f"✅ vertexai imported successfully (version: {vertexai.__version__})")
        
        from vertexai import rag
        print("✅ vertexai.rag imported successfully")
        
        from google.cloud import storage
        print("✅ google.cloud.storage imported successfully")
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test Vertex AI initialization
    try:
        print("🔄 Testing Vertex AI initialization...")
        vertexai.init(project=project_id, location="us-central1")
        print("✅ Vertex AI initialized successfully")
    except Exception as e:
        print(f"❌ Vertex AI initialization failed: {e}")
        return False
    
    # Test storage client
    try:
        print("🔄 Testing Storage client...")
        storage_client = storage.Client(project=project_id)
        print("✅ Storage client created successfully")
    except Exception as e:
        print(f"❌ Storage client failed: {e}")
        return False
    
    print("-" * 40)
    print("🎉 All tests passed! Your setup is ready.")
    print("📋 Next steps:")
    print("   1. Add documents to ./documents/ folder")
    print("   2. Run the corpus creation script")
    print("   3. Launch Streamlit app")
    
    return True

if __name__ == "__main__":
    success = test_vertex_ai_setup()
    sys.exit(0 if success else 1) 