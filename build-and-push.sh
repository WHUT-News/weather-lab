#!/bin/bash

# Exit on error
set -e

# Configuration variables
PROJECT_ID=$(gcloud config get-value project)
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-weather-agent}"
TAG="${TAG:-latest}"

# Construct full image path
IMAGE_PATH="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${TAG}"
echo "================================================"
echo "Building and pushing Docker image"
echo "================================================"
echo "Project ID: ${PROJECT_ID}"
echo "Service Name: ${SERVICE_NAME}"
echo "Tag: ${TAG}"
echo "Image Path: ${IMAGE_PATH}"
echo "================================================"

# Build the Docker image
echo "Building Docker image..."
docker build -t "${IMAGE_PATH}" .

# Push the image to GCR
echo "Pushing image to Google Container Registry..."
docker push "${IMAGE_PATH}"

echo "================================================"
echo "Build and push completed successfully!"
echo "Image: ${IMAGE_PATH}"
echo "================================================"
echo ""
echo "Now run ./deploy-cloudrun.sh to deploy this image to Cloud Run"
