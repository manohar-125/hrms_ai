#!/bin/bash

# Docker Build and Push Script
# Push image to Docker Hub for production use

set -e

DOCKER_USERNAME="manohar12500"
IMAGE_NAME="hrms_ai"
IMAGE_TAG="latest"
FULL_IMAGE="$DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"

echo "=========================================="
echo "Building Docker Image for Production"
echo "=========================================="
echo "Image: $FULL_IMAGE"
echo ""

# Build the image
echo "📦 Building image..."
docker build -f docker/Dockerfile -t $FULL_IMAGE .

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build successful!"
echo ""

# Login to Docker Hub
echo "🔐 Logging into Docker Hub..."
docker login

if [ $? -ne 0 ]; then
    echo "❌ Docker login failed!"
    exit 1
fi

echo ""
echo "📤 Pushing image to Docker Hub..."
docker push $FULL_IMAGE

if [ $? -ne 0 ]; then
    echo "❌ Push failed!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Successfully pushed: $FULL_IMAGE"
echo "=========================================="
echo ""
echo "Next steps on other systems:"
echo "1. Clone the repo: git clone <repo>"
echo "2. Copy env file: cp docker/.env.example .env"
echo "3. Edit .env with your credentials"
echo "4. Start services:"
echo "   docker-compose -f docker/docker-compose.yml up -d"
echo ""
