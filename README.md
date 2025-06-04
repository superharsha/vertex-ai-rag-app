# 🤖 Document Query System

**AI-Powered Document Querying with Google Vertex AI RAG Engine**

Query your document collection using natural language with advanced AI powered by Google's Gemini 2.0 Flash and Vertex AI RAG technology.

## 🚀 Live Demo

[**Launch App on Streamlit Cloud →**](https://your-app-url-here)

## ✨ Features

- 🤖 **Enhanced Generation** using Gemini 2.0 Flash with RAG
- 🔍 **Direct Retrieval** showing raw document context  
- 📊 **Preset Response Styles** (Analytical Expert, Executive Summary, etc.)
- ⚙️ **Adjustable Document Depth** (1-10 sections)
- 🎯 **Custom System Prompts** for specialized responses
- 🏢 **Enterprise-Ready** with Google Cloud authentication

## 📚 Knowledge Base

The system contains **56 documents** including:
- HealthSync project documentation
- RFP documents and requirements  
- Business reports and contracts
- Technical specifications
- Financial information

## 🛠️ Quick Start

### For Streamlit Cloud Deployment

1. **Fork this repository** to your GitHub account

2. **Connect to Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub account
   - Select this repository
   - Choose `app.py` as your main file

3. **Configure Secrets:**
   - In Streamlit Cloud dashboard, go to **App settings → Secrets**
   - Copy your Google Cloud service account JSON and paste it in this format:
   
   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\nYOUR-PRIVATE-KEY-CONTENT\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@your-project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
   ```

4. **Deploy** - Your app will be live in minutes!

### For Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/vertex-ai-rag-standalone.git
   cd vertex-ai-rag-standalone
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up authentication:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ```

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

## 🎯 Usage Examples

### Sample Queries

- **Project Information:** "What are the key requirements in the HealthSync project?"
- **Financial Analysis:** "Summarize financial information about Valenbridge Global"
- **Risk Assessment:** "What are the main risks identified across all projects?"
- **Technical Details:** "Show me technical specifications from RFP documents"

### Response Styles

- **📊 Analytical Expert:** Detailed, structured responses with clear reasoning
- **📋 Executive Summary:** Concise, high-level business insights
- **🔧 Technical Specialist:** In-depth technical explanations
- **📅 Project Manager:** Focus on timelines, deliverables, and resources
- **💰 Financial Analyst:** Cost, budget, and ROI analysis
- **⚖️ Compliance Officer:** Regulations and standards focus

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │ ←→ │   Vertex AI RAG  │ ←→ │ Google Cloud    │
│                 │    │   Engine         │    │ Storage         │
│ • Query Input   │    │                  │    │                 │
│ • Response      │    │ • Gemini 2.0     │    │ • 56 Documents  │
│ • Settings      │    │ • Embeddings     │    │ • Processed     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔧 Technical Details

- **AI Model:** Gemini 2.0 Flash (`gemini-2.0-flash-001`)
- **Embedding Model:** `text-embedding-005`
- **Knowledge Base:** 56 documents processed and indexed
- **Corpus ID:** `ragCorpora/2738188573441261568`
- **Location:** `us-central1`

## 📋 Requirements

- Google Cloud Project with Vertex AI enabled
- Service Account with necessary permissions:
  - Vertex AI User
  - Storage Object Viewer
- Python 3.8+
- Dependencies listed in `requirements.txt`

## 🔐 Security

- Service account credentials stored securely in Streamlit secrets
- No sensitive data exposed in code
- All API calls authenticated with Google Cloud IAM
- Follows Google Cloud security best practices

## 🚀 Deployment

This app is ready for deployment on:
- **Streamlit Cloud** (Recommended)
- Google Cloud Run
- Any Python hosting platform

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

For issues or questions:
- Open a GitHub issue
- Check the troubleshooting section in the wiki
- Review Google Cloud Vertex AI documentation

---

**Built with ❤️ using Google Vertex AI, Streamlit, and Gemini 2.0 Flash** 