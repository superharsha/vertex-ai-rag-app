# 🚀 Streamlit Cloud Deployment Guide

## Prerequisites

1. **GitHub Account** - Your code must be in a GitHub repository
2. **Google Cloud Project** - With Vertex AI API enabled
3. **Service Account** - Create one with appropriate permissions

## 📋 Environment Variables Needed

```bash
PROJECT_ID = "YOUR_PROJECT_ID"
```

## 🔑 Service Account Configuration

Create a service account JSON with these fields:
```json
{
  "type": "service_account",
  "project_id": "YOUR_PROJECT_ID",
  "private_key_id": "YOUR_PRIVATE_KEY_ID",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n",
  "client_email": "YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com",
  "client_id": "YOUR_CLIENT_ID",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/YOUR_SERVICE_ACCOUNT%40YOUR_PROJECT_ID.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

## 🔒 Security Notes

- **NEVER** commit private keys to git repositories
- Use environment variables or secrets management
- Rotate keys regularly
- Grant minimal required permissions

## 📝 Deployment Steps

1. Create GitHub repository with your code
2. Go to https://share.streamlit.io/
3. Connect your repository 
4. Set main file: `streamlit_standalone.py`
5. Add secrets in Streamlit Cloud settings (NOT in code)
6. Deploy the application

---
*Remember: Keep your credentials secure and never expose them publicly!* 