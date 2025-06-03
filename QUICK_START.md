# 🚀 Vertex AI RAG - Quick Start Guide

## 📍 **Project Location**
```
/Users/sr/externalRepos/vertex-ai-rag-standalone
```

## ✅ **What's Ready**
- ✅ **GitHub Repository**: https://github.com/superharsha/vertex-ai-rag-app.git
- ✅ **Service Account**: `YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com`
- ✅ **All Files**: Standalone project with all RAG components
- ✅ **Local Testing**: App works locally on port 8502

## 🚀 **Quick Commands**

### **Local Development**
```bash
# Install dependencies
pip install -r requirements.txt

# Run standalone Streamlit app
streamlit run streamlit_standalone.py --server.port 8502

# Run full system (FastAPI + Streamlit)
./start_vertex_rag.sh

# Stop full system
./stop_vertex_rag.sh
```

### **Streamlit Cloud Deployment**
1. **Go to**: https://share.streamlit.io/
2. **Connect**: GitHub account
3. **Select**: `vertex-ai-rag-app` repository
4. **Main file**: `streamlit_standalone.py`
5. **Add secrets**: Configure service account credentials in Streamlit Cloud secrets

## 📁 **Key Files**
- `streamlit_standalone.py` - **Main app for Streamlit Cloud**
- `fastapi_vertex_rag.py` - FastAPI backend
- `requirements.txt` - Dependencies for Streamlit Cloud
- `README_DEPLOYMENT.md` - **Deployment guide template**

## 🎯 **Live App URL**
After deployment: `https://vertex-ai-rag-app-[random-id].streamlit.app`

## 🔧 **Features**
- ✅ **Multi-format Upload**: PDF, DOCX, TXT
- ✅ **Multiple AI Models**: Latest Gemini models
- ✅ **Custom System Prompts**: Tailor AI responses
- ✅ **Auto GCS Buckets**: Automatic cloud storage
- ✅ **Real-time RAG**: Instant document analysis

## 🔒 **Security Notes**
- Never commit private keys or credentials to git
- Use Streamlit Cloud secrets for sensitive configuration
- Configure service account with minimal required permissions

---
*Ready to deploy! Set up your credentials securely before deployment.* 