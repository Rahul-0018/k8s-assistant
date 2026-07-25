#!/bin/bash
set -e

NAMESPACE="chatbotai"

echo "🚀 Deploying Chatbot to Kubernetes..."

# Apply manifests in order
echo "📁 Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "⚙️  Applying ConfigMap..."
kubectl apply -f k8s/configmap.yaml

echo "🔐 Applying Secret..."
kubectl apply -f k8s/secret.yaml

echo "📦 Applying Deployment..."
kubectl apply -f k8s/deployment.yaml

echo "🔌 Applying Service..."
kubectl apply -f k8s/service.yaml

echo "🌐 Applying Ingress..."
kubectl apply -f k8s/ingress.yaml

echo "🔒 Applying NetworkPolicy..."
kubectl apply -f k8s/networkpolicy.yaml

echo "🛡️  Applying PodDisruptionBudget..."
kubectl apply -f k8s/pdb.yaml

echo "📊 Applying ServiceMonitor..."
kubectl apply -f k8s/servicemonitor.yaml

echo "⏳ Waiting for rollout..."
kubectl rollout status deployment/chatbotai -n $NAMESPACE --timeout=300s

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Current status:"
kubectl get pods -n $NAMESPACE
kubectl get svc -n $NAMESPACE
kubectl get ingress -n $NAMESPACE

echo ""
echo "🧪 Running smoke tests..."
# Port-forward for testing
kubectl port-forward svc/chatbotai-service 8080:80 -n $NAMESPACE &
PF_PID=$!
sleep 3

curl -sf http://localhost:8080/health && echo "✅ Health check passed"
curl -sf http://localhost:8080/api/models && echo "✅ Models endpoint passed"

kill $PF_PID 2>/dev/null || true

echo ""
echo "🎉 All done! Access your chatbot via the Ingress URL or port-forward:"
echo "   kubectl port-forward svc/chatbotai-service 8080:80 -n $NAMESPACE"
echo "   Then open: http://localhost:8080"
