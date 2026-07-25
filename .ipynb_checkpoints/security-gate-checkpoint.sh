#!/bin/bash
set -e

echo "🔒 Running security gates..."

# Build image
docker build -t chatbotai:scan .

# Trivy scan - fail on HIGH/CRITICAL
echo "📋 Scanning for vulnerabilities..."
trivy image --exit-code 1 --severity HIGH,CRITICAL groq-chatbot:scan

# Check for secrets
echo "🔍 Scanning for secrets..."
trivy filesystem --scanners secret .

# Check Dockerfile best practices
echo "📝 Checking Dockerfile..."
if grep -q "USER root" Dockerfile; then
    echo "❌ ERROR: Dockerfile runs as root"
    exit 1
fi

if ! grep -q "HEALTHCHECK" Dockerfile; then
    echo "❌ ERROR: Dockerfile missing HEALTHCHECK"
    exit 1
fi

# Check for hardcoded secrets
echo "🔐 Checking for hardcoded secrets..."
if grep -r "gsk_" --include="*.py" --include="*.yaml" --include="*.yml" . | grep -v "example\|YOUR_\|README"; then
    echo "❌ ERROR: Potential hardcoded Groq API key found"
    exit 1
fi

echo "✅ All security gates passed!"
