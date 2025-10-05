#!/bin/bash
# Google Cloud Deployment Script for ExoSense API

set -e

# Configuration
PROJECT_ID=${1:-"exo-sense"}
REGION=${2:-"europe-west1"}  # Default to Europe West 1 (Belgium - closest to Portugal)
SERVICE_NAME="exosense-api"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Deploying ExoSense API to Google Cloud Run"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build and push container
echo "🏗️ Building container..."
gcloud builds submit --tag $IMAGE_NAME ./api

# Deploy to Cloud Run with free tier settings
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10 \
    --min-instances 0 \
    --timeout 300s \
    --concurrency 10 \
    --port 8080

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo "📊 API Docs: $SERVICE_URL/docs"
echo "❤️ Health Check: $SERVICE_URL/healthz"

echo ""
echo "🔧 Next steps:"
echo "1. Update frontend NEXT_PUBLIC_API_URL to: $SERVICE_URL"
echo "2. Deploy frontend to Vercel"
echo "3. Test end-to-end integration"