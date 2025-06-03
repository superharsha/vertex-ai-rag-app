# 🔒 SECURE Deployment Guide - Vertex AI RAG

## 🚨 SECURITY FIRST!

**NEVER commit credentials to git repositories!** This guide shows you how to deploy securely.

## 🛠️ Prerequisites Setup

### 1. Create Google Cloud Service Account

```bash
# Set your project ID
export PROJECT_ID="your-actual-project-id"

# Create service account
gcloud iam service-accounts create vertex-rag-app \
    --display-name="Vertex AI RAG App" \
    --project=$PROJECT_ID

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vertex-rag-app@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vertex-rag-app@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

# Create and download key
gcloud iam service-accounts keys create vertex-rag-key.json \
    --iam-account=vertex-rag-app@$PROJECT_ID.iam.gserviceaccount.com
```

### 2. Secure the Key File

```bash
# IMPORTANT: Keep this file secure and NEVER commit it to git!
# Add to .gitignore
echo "vertex-rag-key.json" >> .gitignore
echo "*.json" >> .gitignore
echo ".env" >> .gitignore
```

## 🚀 Streamlit Cloud Deployment

### Step 1: Prepare Repository
1. Ensure no credentials are in your code
2. Push clean code to GitHub
3. Verify no sensitive data in git history

### Step 2: Deploy on Streamlit Cloud
1. Go to https://share.streamlit.io/
2. Click "New app"
3. Select your repository: `vertex-ai-rag-app`
4. Set main file: `streamlit_standalone.py`

### Step 3: Configure Secrets (SECURE METHOD)

In Streamlit Cloud App Settings > Secrets, add:

```toml
# DO NOT copy the actual values here - use your own!
[gcp_service_account]
type = "service_account"
project_id = "your-actual-project-id"
private_key_id = "your-key-id"
private_key = """-----BEGIN PRIVATE KEY-----
your-actual-private-key-content-here
-----END PRIVATE KEY-----"""
client_email = "vertex-rag-app@your-actual-project-id.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/vertex-rag-app%40your-actual-project-id.iam.gserviceaccount.com"
universe_domain = "googleapis.com"
```

## 🔄 If Your Credentials Were Compromised

### 1. Revoke Compromised Service Account
```bash
# Delete the compromised service account
gcloud iam service-accounts delete vertex-rag-streamlit@vpc-host-nonprod-kk186-dr143.iam.gserviceaccount.com --project=vpc-host-nonprod-kk186-dr143
```

### 2. Create New Service Account
```bash
# Create new service account with different name
gcloud iam service-accounts create vertex-rag-secure \
    --display-name="Vertex AI RAG Secure" \
    --project=$PROJECT_ID
```

### 3. Grant Permissions to New Account
```bash
# Grant minimal required permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vertex-rag-secure@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vertex-rag-secure@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

## 🔐 Security Best Practices

1. **Never commit credentials** to any repository
2. **Use environment variables** for local development
3. **Rotate keys regularly** (every 90 days)
4. **Grant minimal permissions** only
5. **Monitor access logs** regularly
6. **Use Streamlit Cloud secrets** for deployment
7. **Enable audit logging** in Google Cloud

## 🚨 Emergency Response

If credentials are exposed:
1. **Immediately revoke** the service account
2. **Remove from git history** (as we did)
3. **Create new service account** with new keys
4. **Update all deployments** with new credentials
5. **Monitor for unauthorized usage**

## ✅ Verification Checklist

- [ ] No credentials in git repository
- [ ] No credentials in git history
- [ ] Service account has minimal permissions
- [ ] Secrets properly configured in Streamlit Cloud
- [ ] Old compromised keys revoked
- [ ] `.gitignore` includes credential files

---

**Remember: Security is not optional. Always protect your credentials!** 