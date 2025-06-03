# 🤖 Vertex AI RAG System

A comprehensive Retrieval-Augmented Generation (RAG) system built with Google Cloud Vertex AI, FastAPI, and Streamlit. This system allows you to upload multiple documents (PDF, DOCX, TXT, MD) and query them using Google's Gemini models with intelligent context retrieval.

## 🌟 Features

- **Multi-format Document Support**: PDF, DOCX, TXT, and Markdown files
- **Vertex AI Integration**: Leverages Google Cloud's RAG API for intelligent document retrieval
- **Modern Web Interface**: Beautiful Streamlit frontend with responsive design
- **RESTful API**: Complete FastAPI backend with automatic documentation
- **Google Cloud Storage**: Automatic document storage and management
- **Real-time Processing**: Asynchronous document processing and querying
- **Comprehensive Logging**: Detailed logs for monitoring and debugging

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │    FastAPI      │    │   Vertex AI     │
│   Frontend      │───▶│    Backend      │───▶│   RAG API       │
│  (Port 8501)    │    │  (Port 8000)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Users       │    │  Document       │    │  Google Cloud   │
│   Interface     │    │  Processing     │    │    Storage      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud Project**: Set up a GCP project with Vertex AI API enabled
2. **Google Cloud Storage**: Create a GCS bucket for document storage
3. **Authentication**: Configure Google Cloud credentials
4. **Python**: Python 3.11+ installed

### 1. Environment Setup

1. Copy the environment template:
```bash
cp .env.template .env
```

2. Edit `.env` with your Google Cloud configuration:
```bash
PROJECT_ID=your-gcp-project-id
LOCATION=us-central1
GCS_BUCKET=your-gcs-bucket-name
GEN_MODEL=gemini-2.0-flash-001
```

3. Set up Google Cloud authentication:
```bash
# Option 1: Using gcloud CLI (recommended)
gcloud auth application-default login

# Option 2: Using service account key
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
```

### 2. Install Dependencies

```bash
pip install -r requirements_vertex_rag.txt
```

### 3. Start the System

```bash
./start_vertex_rag.sh
```

The system will start both the FastAPI backend and Streamlit frontend:
- **Frontend**: http://localhost:8501
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 4. Stop the System

```bash
./stop_vertex_rag.sh
```

## 📚 Usage Guide

### Web Interface (Streamlit)

1. **Upload Documents**: 
   - Go to the "Upload Documents" tab
   - Select multiple PDF, DOCX, TXT, or MD files
   - Configure chunk size and overlap settings
   - Click "Upload Documents"

2. **Query Documents**:
   - Navigate to the "Query Documents" tab
   - Enter your question in the text area
   - Adjust retrieval settings (top_k, threshold)
   - Click "Search" to get AI-powered answers

3. **Document Library**:
   - View all uploaded documents
   - See file details, sizes, and upload times
   - Clear all documents if needed

4. **Settings**:
   - View system configuration
   - Check API endpoints
   - Monitor system status

### API Endpoints

The FastAPI backend provides the following endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/status` | System status |
| GET | `/documents` | List all documents |
| GET | `/corpus` | Get corpus information |
| POST | `/upload` | Upload documents |
| POST | `/query` | Query documents |
| POST | `/clear` | Clear all documents |
| DELETE | `/documents/{id}` | Delete specific document |

### API Usage Examples

```bash
# Check system status
curl -X GET "http://localhost:8000/status"

# Upload documents
curl -X POST "http://localhost:8000/upload" \
  -F "files=@document1.pdf" \
  -F "files=@document2.docx" \
  -F "description=Research papers"

# Query documents
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings?",
    "top_k": 3,
    "distance_threshold": 0.5
  }'
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_ID` | Google Cloud Project ID | Required |
| `LOCATION` | GCP region | `us-central1` |
| `GCS_BUCKET` | Cloud Storage bucket name | Required |
| `GEN_MODEL` | Gemini model for generation | `gemini-2.0-flash-001` |
| `CHUNK_SIZE` | Text chunk size for processing | `512` |
| `CHUNK_OVERLAP` | Overlap between chunks | `100` |
| `TOP_K` | Number of results to retrieve | `3` |
| `DISTANCE_THRESHOLD` | Minimum relevance score | `0.5` |

### Google Cloud Setup

1. **Enable APIs**:
```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage-component.googleapis.com
```

2. **Create Storage Bucket**:
```bash
gsutil mb gs://your-bucket-name
```

3. **Set IAM Permissions**:
   - Vertex AI User
   - Storage Object Admin
   - AI Platform Admin

## 📊 Monitoring and Logs

### Log Files

- **Backend Logs**: `VertexAIRAG_Logs/backend.log`
- **Frontend Logs**: `VertexAIRAG_Logs/frontend.log`

### Monitoring Commands

```bash
# Monitor backend logs
tail -f VertexAIRAG_Logs/backend.log

# Monitor frontend logs
tail -f VertexAIRAG_Logs/frontend.log

# Check system processes
ps aux | grep -E "(fastapi_vertex_rag|streamlit_vertex_rag)"
```

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Ensure Google Cloud credentials are properly configured
   - Check that the service account has necessary permissions
   - Verify PROJECT_ID is correct

2. **Module Import Errors**:
   - Install all dependencies: `pip install -r requirements_vertex_rag.txt`
   - Check Python version (3.11+ required)

3. **Port Already in Use**:
   - Stop existing processes: `./stop_vertex_rag.sh`
   - Check for other applications using ports 8000 or 8501

4. **GCS Bucket Issues**:
   - Verify bucket exists and is accessible
   - Check bucket permissions
   - Ensure bucket name is globally unique

### Debug Mode

To run in debug mode:

1. Set `DEBUG=True` in `.env`
2. Start services manually:
```bash
# Backend
python fastapi_vertex_rag.py

# Frontend (in another terminal)
streamlit run streamlit_vertex_rag.py
```

## 🚀 Advanced Features

### Custom Document Processing

The system supports custom chunk sizes and overlap settings for optimal retrieval performance based on your document types.

### Multi-language Support

Vertex AI RAG supports multiple languages. Simply upload documents in different languages and query in the same language.

### Scalability

- Asynchronous processing for large documents
- Efficient memory management
- Support for thousands of documents

## 📝 Development

### Project Structure

```
dataPipeline-KGExtraction/
├── fastapi_vertex_rag.py      # FastAPI backend
├── streamlit_vertex_rag.py    # Streamlit frontend
├── start_vertex_rag.sh        # Startup script
├── stop_vertex_rag.sh         # Stop script
├── requirements_vertex_rag.txt # Dependencies
├── .env.template              # Environment template
├── .env                       # Your configuration
├── VertexAIRAG_Logs/         # Log directory
│   ├── backend.log
│   ├── frontend.log
│   ├── backend.pid
│   └── frontend.pid
└── README_VertexAI_RAG.md    # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

For support and questions:

1. Check the troubleshooting section
2. Review the logs in `VertexAIRAG_Logs/`
3. Consult Google Cloud Vertex AI documentation
4. Open an issue in the repository

## 🎯 Roadmap

- [ ] Support for additional file formats (PPT, XLS)
- [ ] Advanced search filters and facets
- [ ] Batch document processing
- [ ] User authentication and authorization
- [ ] Document versioning and history
- [ ] Custom model fine-tuning integration
- [ ] Advanced analytics and usage metrics

---

**Happy querying! 🚀** 