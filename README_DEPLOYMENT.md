# 🚀 Streamlit Cloud Deployment Files

## Files to Upload to GitHub Repository:

1. **streamlit_standalone.py** - Main application file
2. **requirements.txt** - Dependencies (rename from requirements_streamlit_cloud.txt)
3. **README.md** - This file

## Streamlit Cloud Configuration:

### Required Secrets:
```toml
PROJECT_ID = "vpc-host-nonprod-kk186-dr143"

[gcp_service_account]
type = "service_account"
project_id = "vpc-host-nonprod-kk186-dr143"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
client_email = "vertex-rag-service@vpc-host-nonprod-kk186-dr143.iam.gserviceaccount.com"
client_id = "YOUR_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/vertex-rag-service%40vpc-host-nonprod-kk186-dr143.iam.gserviceaccount.com"
```

## Deployment Steps:

1. Create GitHub repository
2. Upload the 3 files above
3. Deploy on Streamlit Cloud
4. Add secrets in Streamlit Cloud settings
5. Done! 🎉 